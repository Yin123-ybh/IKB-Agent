from __future__ import annotations

from functools import lru_cache

from ..services import ImportService, QueryService, TaskService
from ..settings import get_settings
from ..storage import JsonKnowledgeStore


@lru_cache(maxsize=1)
def get_store() -> JsonKnowledgeStore:
    return JsonKnowledgeStore(get_settings().store_path)


def get_import_service() -> ImportService:
    return ImportService(get_settings(), get_store())


def get_query_service() -> QueryService:
    return QueryService(get_store())


def get_task_service() -> TaskService:
    return TaskService(get_store())

