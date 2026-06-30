from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from datetime import datetime

from .models import ChunkRecord, DocumentRecord, ImportTaskRecord, SearchHit
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
            self._write({"documents": [], "chunks": [], "tasks": []})

    def _read(self) -> dict:
        with self._lock:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
                data.setdefault("documents", [])
                data.setdefault("chunks", [])
                data.setdefault("tasks", [])
                return data

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

    def upsert_task(self, task: ImportTaskRecord) -> None:
        data = self._read()
        data["tasks"] = [item for item in data["tasks"] if item["task_id"] != task.task_id]
        data["tasks"].append(task.model_dump())
        self._write(data)

    def update_task(self, task_id: str, **updates) -> ImportTaskRecord:
        data = self._read()
        existing = next((item for item in data["tasks"] if item["task_id"] == task_id), None)
        if existing is None:
            existing = {"task_id": task_id, "file_name": "", "status": "pending"}
        existing.update(updates)
        existing["updated_at"] = datetime.now().isoformat(timespec="seconds")
        task = ImportTaskRecord(**existing)
        data["tasks"] = [item for item in data["tasks"] if item["task_id"] != task_id]
        data["tasks"].append(task.model_dump())
        self._write(data)
        return task

    def get_task(self, task_id: str) -> ImportTaskRecord | None:
        data = self._read()
        for item in data["tasks"]:
            if item["task_id"] == task_id:
                return ImportTaskRecord(**item)
        return None

    def list_tasks(self) -> list[ImportTaskRecord]:
        data = self._read()
        return [ImportTaskRecord(**item) for item in sorted(data["tasks"], key=lambda row: row["created_at"], reverse=True)]

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
