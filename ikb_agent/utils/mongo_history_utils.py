from __future__ import annotations

from datetime import datetime
from typing import Any

from ..settings import Settings, get_settings


class MongoHistoryStore:
    """Chat history and task trace storage adapter."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        try:
            from pymongo import MongoClient
        except ImportError as exc:
            raise RuntimeError("Install middleware dependencies first: pip install -e '.[middleware]'") from exc
        self.client = MongoClient(self.settings.mongo_url)
        self.db = self.client[self.settings.mongo_db_name]

    def ping(self) -> bool:
        self.client.admin.command("ping")
        return True

    def append_message(self, session_id: str, role: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        result = self.db.chat_history.insert_one(
            {
                "session_id": session_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "created_at": datetime.now(),
            }
        )
        return str(result.inserted_id)

    def list_messages(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        cursor = (
            self.db.chat_history.find({"session_id": session_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        return list(reversed([{**item, "_id": str(item["_id"])} for item in cursor]))

