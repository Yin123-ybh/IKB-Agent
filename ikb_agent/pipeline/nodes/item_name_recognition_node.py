from __future__ import annotations

from .base import BasePipelineNode
from ..state import ImportState
from ...text_utils import guess_item_name


class ItemNameRecognitionNode(BasePipelineNode):
    """Identify item name and tag every chunk with it."""

    name = "item_name_recognition_node"

    def process(self, state: ImportState) -> ImportState:
        chunks = state.get("chunks", [])
        context = self._prepare_context(chunks)
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

