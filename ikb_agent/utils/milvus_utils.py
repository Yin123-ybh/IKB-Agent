from __future__ import annotations

from ..models import ChunkRecord
from ..settings import Settings, get_settings
from .embedding_utils import dense_dict_to_list


class MilvusVectorStore:
    """Milvus adapter matching the production architecture in the courseware."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        try:
            from pymilvus import MilvusClient
        except ImportError as exc:
            raise RuntimeError("Install middleware dependencies first: pip install -e '.[middleware]'") from exc
        self.client = MilvusClient(uri=self.settings.milvus_url)

    def ping(self) -> bool:
        self.client.list_collections()
        return True

    def ensure_chunk_collection(self) -> None:
        if self.settings.chunks_collection in self.client.list_collections():
            return
        self.client.create_collection(
            collection_name=self.settings.chunks_collection,
            dimension=self.settings.embedding_dim,
            metric_type=self.settings.milvus_metric_type,
            auto_id=False,
            id_type="string",
            max_length=64,
        )

    def upsert_chunks(self, chunks: list[ChunkRecord]) -> int:
        self.ensure_chunk_collection()
        rows = []
        for chunk in chunks:
            rows.append(
                {
                    "id": chunk.chunk_id,
                    "vector": dense_dict_to_list(chunk.dense_vector, self.settings.embedding_dim),
                    "document_id": chunk.document_id,
                    "title": chunk.title,
                    "item_name": chunk.item_name,
                    "file_title": chunk.file_title,
                    "content": chunk.content,
                }
            )
        if rows:
            self.client.upsert(collection_name=self.settings.chunks_collection, data=rows)
        return len(rows)

