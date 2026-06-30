from __future__ import annotations

from .base import BasePipelineNode
from ..state import ImportState
from ...text_utils import sparse_vectorize, vectorize


class EmbeddingNode(BasePipelineNode):
    """Generate local dense/sparse vectors for chunks."""

    name = "bge_embedding_chunks_node"

    def process(self, state: ImportState) -> ImportState:
        for chunk in state.get("chunks", []):
            embedding_text = f"{chunk.get('item_name', '')}\n{chunk.get('content', '')}"
            chunk["dense_vector"] = vectorize(embedding_text)
            chunk["sparse_vector"] = sparse_vectorize(embedding_text)
        return state

