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
    max_chunk_chars: int = int(os.getenv("MAX_CHUNK_CHARS", "1200"))
    min_chunk_chars: int = int(os.getenv("MIN_CHUNK_CHARS", "260"))
    item_name_chunk_k: int = int(os.getenv("ITEM_NAME_CHUNK_K", "3"))
    item_name_context_chars: int = int(os.getenv("ITEM_NAME_CONTEXT_CHARS", "2400"))
    search_top_k: int = int(os.getenv("SEARCH_TOP_K", "5"))

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "")
    llm_model: str = os.getenv("LLM_MODEL", "qwen-flash")
    vl_model: str = os.getenv("VL_MODEL", "qwen3-vl-flash")
    enable_external_llm: bool = _bool_env("ENABLE_EXTERNAL_LLM", False)

    milvus_url: str = os.getenv("MILVUS_URL", "")
    chunks_collection: str = os.getenv("CHUNKS_COLLECTION", "ikb_chunks")
    item_name_collection: str = os.getenv("ITEM_NAME_COLLECTION", "ikb_item_names")

    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "")
    minio_bucket_name: str = os.getenv("MINIO_BUCKET_NAME", "ikb-agent")

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

