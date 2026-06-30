from __future__ import annotations

from functools import lru_cache

from ..services import ImportService, QueryService, TaskService
from ..settings import get_settings
from ..storage import HybridKnowledgeStore, JsonKnowledgeStore


@lru_cache(maxsize=1)
def get_store():
    settings = get_settings()
    json_store = JsonKnowledgeStore(settings.store_path)
    if settings.store_backend in {"milvus", "middleware"}:
        return HybridKnowledgeStore(settings, json_store)
    return json_store


def get_import_service() -> ImportService:
    return ImportService(get_settings(), get_store())


def get_query_service() -> QueryService:
    return QueryService(get_store())


def get_task_service() -> TaskService:
    return TaskService(get_store())
