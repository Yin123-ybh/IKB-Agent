from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any


def sse_event(event: str, data: Any) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def stream_answer_tokens(answer: str) -> Iterable[str]:
    for token in answer:
        yield sse_event("token", {"content": token})
    yield sse_event("done", {"ok": True})

