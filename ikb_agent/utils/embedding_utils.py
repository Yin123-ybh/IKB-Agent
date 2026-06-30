from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..settings import Settings, get_settings
from ..text_utils import sparse_vectorize, vectorize


@dataclass
class EmbeddingResult:
    text: str
    dense_vector: dict[str, float]
    sparse_vector: dict[str, float]


class LocalEmbeddingClient:
    """Lightweight BGE-M3 stand-in used by the local test mode."""

    def embed_documents(self, texts: Iterable[str]) -> list[EmbeddingResult]:
        return [
            EmbeddingResult(
                text=text,
                dense_vector=vectorize(text),
                sparse_vector=sparse_vectorize(text),
            )
            for text in texts
        ]

    def embed_query(self, text: str) -> EmbeddingResult:
        return self.embed_documents([text])[0]


def get_embedding_client(settings: Settings | None = None) -> LocalEmbeddingClient:
    settings = settings or get_settings()
    if settings.embedding_model.lower() not in {"local", "local-hash", "bge-m3"}:
        raise ValueError(f"Unsupported EMBEDDING_MODEL={settings.embedding_model!r}")
    return LocalEmbeddingClient()


def dense_dict_to_list(vector: dict[str, float], dim: int) -> list[float]:
    dense = [0.0] * dim
    for key, value in vector.items():
        index = hash(key) % dim
        dense[index] += float(value)
    return dense

