from __future__ import annotations

from datetime import datetime

from ..models import ImportTaskRecord


def append_trace(task: ImportTaskRecord, message: str) -> ImportTaskRecord:
    task.trace.append(message)
    task.message = message
    task.updated_at = datetime.now().isoformat(timespec="seconds")
    return task

