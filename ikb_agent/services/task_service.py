from __future__ import annotations

from fastapi import HTTPException

from ..storage import JsonKnowledgeStore


class TaskService:
    def __init__(self, store: JsonKnowledgeStore):
        self.store = store

    def list_tasks(self) -> dict:
        return {"tasks": [task.model_dump() for task in self.store.list_tasks()]}

    def get_task(self, task_id: str) -> dict:
        task = self.store.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task.model_dump()

