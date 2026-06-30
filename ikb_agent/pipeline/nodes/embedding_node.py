from __future__ import annotations

from .base import BasePipelineNode
from ..state import ImportState
from ...utils.embedding_utils import get_embedding_client


class EmbeddingNode(BasePipelineNode):
    """Generate dense/sparse vectors for chunks."""

    name = "bge_embedding_chunks_node"

    def process(self, state: ImportState) -> ImportState:
        chunks = state.get("chunks", [])
        embedding_texts = []
        for chunk in chunks:
            embedding_text = f"{chunk.get('item_name', '')}\n{chunk.get('content', '')}"
            embedding_texts.append(embedding_text)
        embedding_results = get_embedding_client(self.settings).embed_documents(embedding_texts)
        for chunk, embedding_result in zip(chunks, embedding_results):
            chunk["dense_vector"] = embedding_result.dense_vector
            chunk["sparse_vector"] = embedding_result.sparse_vector
        return state
