from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "IKB-Agent")
    data_dir: Path = Path(os.getenv("DATA_DIR", "./data"))
    environment: str = os.getenv("ENVIRONMENT", "local")
    store_backend: str = os.getenv("STORE_BACKEND", "json").lower()
    max_chunk_chars: int = int(os.getenv("MAX_CHUNK_CHARS", "1200"))
    min_chunk_chars: int = int(os.getenv("MIN_CHUNK_CHARS", "260"))
    item_name_chunk_k: int = int(os.getenv("ITEM_NAME_CHUNK_K", "3"))
    item_name_context_chars: int = int(os.getenv("ITEM_NAME_CONTEXT_CHARS", "2400"))
    search_top_k: int = int(os.getenv("SEARCH_TOP_K", "5"))

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "")
    llm_model: str = os.getenv("LLM_DEFAULT_MODEL", os.getenv("LLM_MODEL", "qwen-flash"))
    item_model: str = os.getenv("ITEM_MODEL", os.getenv("LLM_DEFAULT_MODEL", "qwen-flash"))
    vl_model: str = os.getenv("VL_MODEL", "qwen3-vl-flash")
    enable_external_llm: bool = _bool_env("ENABLE_EXTERNAL_LLM", False)

    mineru_model_source: str = os.getenv("MINERU_MODEL_SOURCE", "modelscope")
    pdf_parse_backend: str = os.getenv("PDF_PARSE_BACKEND", "pypdf").lower()
    mineru_cli: str = os.getenv("MINERU_CLI", "mineru")
    mineru_method: str = os.getenv("MINERU_METHOD", "auto")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "local-hash")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1024"))
    bge_m3_path: str = os.getenv("BGE_M3_PATH", "")
    bge_m3_name: str = os.getenv("BGE_M3", "BAAI/bge-m3")
    bge_device: str = os.getenv("BGE_DEVICE", "cpu")
    bge_fp16: bool = _bool_env("BGE_FP16", False)
    bge_reranker_path: str = os.getenv("BGE_RERANKER_LARGE", "BAAI/bge-reranker-large")
    bge_reranker_device: str = os.getenv("BGE_RERANKER_DEVICE", "cpu")
    bge_reranker_fp16: bool = _bool_env("BGE_RERANKER_FP16", False)

    milvus_url: str = os.getenv("MILVUS_URL", "http://localhost:19530")
    chunks_collection: str = os.getenv("CHUNKS_COLLECTION", "ikb_chunks")
    item_name_collection: str = os.getenv("ITEM_NAME_COLLECTION", "ikb_item_names")
    milvus_metric_type: str = os.getenv("MILVUS_METRIC_TYPE", "COSINE")
    milvus_min_cosine_score: float = float(os.getenv("MILVUS_MIN_COSINE_SCORE", "0.2"))

    mongo_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "ikb_agent")

    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket_name: str = os.getenv("MINIO_BUCKET_NAME", "ikb-agent")
    minio_secure: bool = _bool_env("MINIO_SECURE", False)

    mcp_dashscope_base_url: str = os.getenv("MCP_DASHSCOPE_BASE_URL", "")

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def store_path(self) -> Path:
        return self.data_dir / "knowledge_store.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
