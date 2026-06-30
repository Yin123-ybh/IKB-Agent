from __future__ import annotations

from .base import BasePipelineNode
from ..state import ImportState
from ...text_utils import guess_item_name
from ...utils.llm_utils import ChatMessage, get_llm_client


class ItemNameRecognitionNode(BasePipelineNode):
    """Identify item name and tag every chunk with it."""

    name = "item_name_recognition_node"

    def process(self, state: ImportState) -> ImportState:
        chunks = state.get("chunks", [])
        context = self._prepare_context(chunks)
        item_name = self._recognize_with_llm(state.get("file_title", ""), context)
        if not item_name:
            item_name = guess_item_name(state.get("file_title", ""), context)
        state["item_name"] = item_name
        for chunk in chunks:
            chunk["item_name"] = item_name
        state["chunks"] = chunks
        return state

    def _prepare_context(self, chunks: list[dict]) -> str:
        pieces: list[str] = []
        total = 0
        for index, chunk in enumerate(chunks[: self.settings.item_name_chunk_k], start=1):
            content = chunk.get("content", "")
            piece = f"【切片】-{index}-{content}"
            if total + len(piece) > self.settings.item_name_context_chars and pieces:
                break
            pieces.append(piece)
            total += len(piece)
        return "\n".join(pieces)

    def _recognize_with_llm(self, file_title: str, context: str) -> str:
        if not self.settings.enable_external_llm:
            return ""
        prompt = (
            "你是企业知识库的商品识别节点。请根据文件名和文档前几个切片识别最核心的商品名、产品名、书名或系统名。"
            "只返回名称本身，不要解释，不要返回 JSON。如果无法判断，返回空字符串。\n\n"
            f"文件名：{file_title}\n\n"
            f"文档切片：\n{context}"
        )
        try:
            result = get_llm_client(self.settings).chat(
                [
                    ChatMessage(role="system", content="你只做名称抽取，输出必须简短。"),
                    ChatMessage(role="user", content=prompt),
                ],
                model=self.settings.item_model,
                timeout=30,
            )
        except Exception:
            return ""
        return self._clean_item_name(result)

    @staticmethod
    def _clean_item_name(value: str) -> str:
        value = (value or "").strip().strip("`\"'“”‘’")
        for prefix in ("商品名：", "商品名称：", "产品名：", "名称：", "书名："):
            if value.startswith(prefix):
                value = value[len(prefix) :].strip()
        value = value.splitlines()[0].strip() if value else ""
        if value in {"无", "未知", "空字符串", "无法判断", "N/A", "None"}:
            return ""
        return value[:80]
