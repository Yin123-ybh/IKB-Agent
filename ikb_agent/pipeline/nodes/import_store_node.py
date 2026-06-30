from __future__ import annotations

from pathlib import Path

from .base import BasePipelineNode
from ..state import ImportState
from ...models import ChunkRecord, DocumentRecord
from ...settings import Settings
from ...storage import JsonKnowledgeStore


class ImportStoreNode(BasePipelineNode):
    """Persist chunk vectors and metadata.

    The node name mirrors the production Milvus import node. Local mode stores
    data in JSON so the project can be tested without middleware.
    """

    name = "milvus_import_node"

    def __init__(self, settings: Settings, store: JsonKnowledgeStore):
        super().__init__(settings)
        self.store = store

    def process(self, state: ImportState) -> ImportState:
        chunks: list[ChunkRecord] = []
        for chunk in state.get("chunks", []):
            chunk_id = f"{state['document_id']}-{chunk['chunk_index']:04d}"
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    document_id=state["document_id"],
                    content=chunk["content"],
                    title=chunk["title"],
                    parent_title=chunk["parent_title"],
                    file_title=chunk["file_title"],
                    item_name=chunk["item_name"],
                    dense_vector=chunk["dense_vector"],
                    sparse_vector=chunk["sparse_vector"],
                    metadata={"chunk_index": chunk["chunk_index"]},
                )
            )

        document = DocumentRecord(
            document_id=state["document_id"],
            file_name=Path(state["import_file_path"]).name,
            file_title=state["file_title"],
            item_name=state.get("item_name", state["file_title"]),
            chunk_count=len(chunks),
        )
        self.store.upsert_document(document, chunks)
        state["document"] = document.model_dump()
        state["chunk_records"] = [chunk.model_dump() for chunk in chunks]
        return state

