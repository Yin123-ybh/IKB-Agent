from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from .models import ChunkRecord, DocumentRecord, SearchHit
from .text_utils import cosine, sparse_overlap, sparse_vectorize, vectorize


class JsonKnowledgeStore:
    """Small local store used for demos and interview review.

    The production design can swap this with Milvus and MinIO without changing
    the pipeline contract: chunks still carry text, metadata, dense vectors, and
    sparse vectors.
    """

    def __init__(self, path: Path):
        self.path = path
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"documents": [], "chunks": []})

    def _read(self) -> dict:
        with self._lock:
            with self.path.open("r", encoding="utf-8") as file:
                return json.load(file)

    def _write(self, data: dict) -> None:
        with self._lock:
            with self.path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)

    def upsert_document(self, document: DocumentRecord, chunks: list[ChunkRecord]) -> None:
        data = self._read()
        data["documents"] = [item for item in data["documents"] if item["document_id"] != document.document_id]
        data["chunks"] = [item for item in data["chunks"] if item["document_id"] != document.document_id]
        data["documents"].append(document.model_dump())
        data["chunks"].extend(chunk.model_dump() for chunk in chunks)
        self._write(data)

    def list_documents(self) -> list[DocumentRecord]:
        data = self._read()
        return [DocumentRecord(**item) for item in sorted(data["documents"], key=lambda row: row["created_at"], reverse=True)]

    def list_chunks(self) -> list[ChunkRecord]:
        data = self._read()
        return [ChunkRecord(**item) for item in data["chunks"]]

    def search(self, query: str, top_k: int = 5, item_names: list[str] | None = None) -> list[SearchHit]:
        query_dense = vectorize(query)
        query_sparse = sparse_vectorize(query)
        filters = {name.strip().lower() for name in item_names or [] if name.strip()}
        hits: list[SearchHit] = []

        for chunk in self.list_chunks():
            if filters and chunk.item_name.lower() not in filters:
                continue
            dense_score = cosine(query_dense, chunk.dense_vector)
            sparse_score = sparse_overlap(query_sparse, chunk.sparse_vector)
            score = 0.64 * dense_score + 0.36 * sparse_score
            if score <= 0:
                continue
            hits.append(
                SearchHit(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    item_name=chunk.item_name,
                    file_title=chunk.file_title,
                    content=chunk.content,
                    score=round(score, 5),
                    dense_score=round(dense_score, 5),
                    sparse_score=round(sparse_score, 5),
                )
            )
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:top_k]

