from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_store, get_task_service
from ..settings import get_settings
from ..storage import JsonKnowledgeStore
from ..services import TaskService

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "store": str(settings.store_path) if settings.store_backend == "json" else settings.milvus_url,
        "mode": "local-json-store" if settings.store_backend == "json" else "milvus-middleware-store",
    }


@router.get("/documents")
def documents(store: JsonKnowledgeStore = Depends(get_store)) -> dict:
    return {"documents": [document.model_dump() for document in store.list_documents()]}


@router.get("/tasks")
def tasks(service: TaskService = Depends(get_task_service)) -> dict:
    return service.list_tasks()


@router.get("/tasks/{task_id}")
def task_detail(task_id: str, service: TaskService = Depends(get_task_service)) -> dict:
    return service.get_task(task_id)
