from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChunkRecord(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    title: str
    parent_title: str
    file_title: str
    item_name: str
    dense_vector: dict[str, float] = Field(default_factory=dict)
    sparse_vector: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRecord(BaseModel):
    document_id: str
    file_name: str
    file_title: str
    item_name: str
    chunk_count: int
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class ImportResponse(BaseModel):
    message: str
    document: DocumentRecord
    chunks: list[ChunkRecord]
    trace: list[str]


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    item_name: str
    file_title: str
    content: str
    score: float
    dense_score: float
    sparse_score: float


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    item_names: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=12)


class QueryResponse(BaseModel):
    answer: str
    hits: list[SearchHit]
    rewritten_query: str
    item_names: list[str]

