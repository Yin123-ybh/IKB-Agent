from __future__ import annotations

from ..models import QueryRequest, QueryResponse
from ..settings import Settings, get_settings
from ..storage import JsonKnowledgeStore
from ..text_utils import guess_item_name, strip_markdown
from ..utils.llm_utils import ChatMessage, get_llm_client


class QueryService:
    """Application service for retrieval and answer assembly."""

    def __init__(self, store: JsonKnowledgeStore, settings: Settings | None = None):
        self.store = store
        self.settings = settings or get_settings()

    def query(self, request: QueryRequest) -> QueryResponse:
        explicit_item_names = [name for name in request.item_names if name.strip()]
        inferred_item_names: list[str] = []
        if not explicit_item_names:
            inferred = guess_item_name("", request.query)
            inferred_item_names = [] if inferred == "未知商品" else [inferred]

        # Only an explicit item filter from the API should narrow the corpus.
        # Auto-inferred names are useful metadata, but using them as a hard
        # filter makes the demo look broken after importing unrelated PDFs.
        hits = self.store.search(request.query, top_k=request.top_k, item_names=explicit_item_names)

        return QueryResponse(
            answer=self._build_answer(request.query, hits),
            hits=hits,
            rewritten_query=request.query.strip(),
            item_names=explicit_item_names or inferred_item_names,
        )

    def _build_answer(self, query: str, hits) -> str:
        if not hits:
            return "暂未检索到足够相关的知识片段。请先导入文档，或换一个更具体的商品名/问题。"
        if self.settings.enable_external_llm:
            answer = self._build_answer_with_llm(query, hits)
            if answer:
                return answer

        top = hits[0]
        evidence = strip_markdown(top.content, limit=520)
        bullet_lines = []
        for index, hit in enumerate(hits[:3], start=1):
            bullet_lines.append(
                f"{index}. {hit.title}（{hit.file_title} / {hit.item_name}，score={hit.score:.3f}）"
            )
        return (
            f"根据已导入知识库，问题「{query.strip()}」最相关的资料来自「{top.title}」。\n\n"
            f"核心依据：{evidence}\n\n"
            "召回来源：\n" + "\n".join(bullet_lines)
        )

    def _build_answer_with_llm(self, query: str, hits) -> str:
        evidence_blocks = []
        for index, hit in enumerate(hits[:5], start=1):
            evidence_blocks.append(
                f"[{index}] 来源：{hit.file_title} / {hit.title} / {hit.item_name} / score={hit.score:.3f}\n"
                f"{strip_markdown(hit.content, limit=900)}"
            )
        prompt = (
            "请基于给定知识片段回答用户问题。要求：\n"
            "1. 只能根据知识片段作答，不要编造。\n"
            "2. 如果资料不足，要明确说资料不足。\n"
            "3. 回答要适合企业知识库问答场景，先给结论，再给依据。\n"
            "4. 末尾列出使用的来源编号。\n\n"
            f"用户问题：{query.strip()}\n\n"
            "知识片段：\n" + "\n\n".join(evidence_blocks)
        )
        try:
            return get_llm_client(self.settings).chat(
                [
                    ChatMessage(role="system", content="你是严谨的企业知识库 RAG 问答助手。"),
                    ChatMessage(role="user", content=prompt),
                ],
                model=self.settings.llm_model,
                timeout=60,
            ).strip()
        except Exception:
            return ""
