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
        from pymilvus import DataType

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=64)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self.settings.embedding_dim)
        schema.add_field(field_name="document_id", datatype=DataType.VARCHAR, max_length=64)
        schema.add_field(field_name="title", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="item_name", datatype=DataType.VARCHAR, max_length=256)
        schema.add_field(field_name="file_title", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=8192)
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type=self.settings.milvus_metric_type,
        )
        self.client.create_collection(
            collection_name=self.settings.chunks_collection,
            schema=schema,
            index_params=index_params,
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
            self.client.flush(collection_name=self.settings.chunks_collection)
        return len(rows)
