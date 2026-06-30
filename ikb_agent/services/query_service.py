from __future__ import annotations

from ..models import QueryRequest, QueryResponse
from ..storage import JsonKnowledgeStore
from ..text_utils import guess_item_name, strip_markdown


class QueryService:
    """Application service for retrieval and answer assembly."""

    def __init__(self, store: JsonKnowledgeStore):
        self.store = store

    def query(self, request: QueryRequest) -> QueryResponse:
        item_names = request.item_names
        if not item_names:
            inferred = guess_item_name("", request.query)
            item_names = [] if inferred == "未知商品" else [inferred]

        hits = self.store.search(request.query, top_k=request.top_k, item_names=item_names)
        if not hits and item_names:
            hits = self.store.search(request.query, top_k=request.top_k, item_names=[])

        return QueryResponse(
            answer=self._build_answer(request.query, hits),
            hits=hits,
            rewritten_query=request.query.strip(),
            item_names=item_names,
        )

    @staticmethod
    def _build_answer(query: str, hits) -> str:
        if not hits:
            return "暂未检索到足够相关的知识片段。请先导入文档，或换一个更具体的商品名/问题。"

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

