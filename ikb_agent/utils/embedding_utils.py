from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Protocol

from ..settings import Settings, get_settings
from ..text_utils import sparse_vectorize, vectorize

DenseVector = dict[str, float] | list[float]
SparseVector = dict[str, float]


@dataclass
class EmbeddingResult:
    text: str
    dense_vector: DenseVector
    sparse_vector: SparseVector


class EmbeddingClient(Protocol):
    def embed_documents(self, texts: Iterable[str]) -> list[EmbeddingResult]:
        ...

    def embed_query(self, text: str) -> EmbeddingResult:
        ...


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


class BgeM3EmbeddingClient:
    """Real BGE-M3 embedding client powered by FlagEmbedding."""

    def __init__(self, settings: Settings):
        try:
            from FlagEmbedding import BGEM3FlagModel
        except ImportError as exc:
            raise RuntimeError("Install BGE dependencies first: pip install -e '.[bge]'") from exc

        model_name_or_path = settings.bge_m3_path or settings.bge_m3_name
        kwargs = {"use_fp16": settings.bge_fp16}
        if settings.bge_device:
            kwargs["device"] = settings.bge_device
        try:
            self.model = BGEM3FlagModel(model_name_or_path, **kwargs)
        except TypeError:
            kwargs.pop("device", None)
            self.model = BGEM3FlagModel(model_name_or_path, **kwargs)

    def embed_documents(self, texts: Iterable[str]) -> list[EmbeddingResult]:
        text_list = list(texts)
        if not text_list:
            return []
        encoded = self.model.encode(
            text_list,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        dense_vectors = encoded.get("dense_vecs")
        if dense_vectors is None:
            dense_vectors = encoded.get("dense") or []
        sparse_output = encoded.get("lexical_weights")
        if sparse_output is None:
            sparse_output = encoded.get("sparse_vecs")
        sparse_vectors = self._extract_sparse_vectors(sparse_output, len(text_list))
        return [
            EmbeddingResult(
                text=text,
                dense_vector=self._to_float_list(dense_vectors[index]),
                sparse_vector=sparse_vectors[index],
            )
            for index, text in enumerate(text_list)
        ]

    def embed_query(self, text: str) -> EmbeddingResult:
        return self.embed_documents([text])[0]

    @staticmethod
    def _to_float_list(vector) -> list[float]:
        if hasattr(vector, "tolist"):
            vector = vector.tolist()
        return [float(value) for value in vector]

    @classmethod
    def _extract_sparse_vectors(cls, sparse_output, size: int) -> list[SparseVector]:
        if sparse_output is None:
            return [{} for _ in range(size)]
        if isinstance(sparse_output, list):
            return [cls._normalize_sparse_dict(item) for item in sparse_output]
        if all(hasattr(sparse_output, attr) for attr in ("indptr", "indices", "data")):
            vectors: list[SparseVector] = []
            for index in range(size):
                start = int(sparse_output.indptr[index])
                end = int(sparse_output.indptr[index + 1])
                token_ids = sparse_output.indices[start:end]
                weights = sparse_output.data[start:end]
                vectors.append({str(token_id): float(weight) for token_id, weight in zip(token_ids, weights)})
            return vectors
        return [{} for _ in range(size)]

    @staticmethod
    def _normalize_sparse_dict(value) -> SparseVector:
        if not isinstance(value, dict):
            return {}
        return {str(key): float(weight) for key, weight in value.items()}


@lru_cache(maxsize=2)
def _get_cached_bge_client(
    bge_m3_path: str,
    bge_m3_name: str,
    bge_device: str,
    bge_fp16: bool,
) -> BgeM3EmbeddingClient:
    settings = Settings(
        bge_m3_path=bge_m3_path,
        bge_m3_name=bge_m3_name,
        bge_device=bge_device,
        bge_fp16=bge_fp16,
        embedding_model="bge-m3",
    )
    return BgeM3EmbeddingClient(settings)


def get_embedding_client(settings: Settings | None = None) -> EmbeddingClient:
    settings = settings or get_settings()
    embedding_model = settings.embedding_model.lower()
    if embedding_model in {"local", "local-hash"}:
        return LocalEmbeddingClient()
    if embedding_model in {"bge-m3", "bge_m3", "bge"}:
        return _get_cached_bge_client(
            settings.bge_m3_path,
            settings.bge_m3_name,
            settings.bge_device,
            settings.bge_fp16,
        )
    raise ValueError(f"Unsupported EMBEDDING_MODEL={settings.embedding_model!r}")


def dense_dict_to_list(vector: DenseVector, dim: int) -> list[float]:
    if isinstance(vector, list):
        if len(vector) == dim:
            return [float(value) for value in vector]
        dense = [0.0] * dim
        for index, value in enumerate(vector[:dim]):
            dense[index] = float(value)
        return dense

    dense = [0.0] * dim
    for key, value in vector.items():
        index = hash(key) % dim
        dense[index] += float(value)
    return dense
