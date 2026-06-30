from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from ..settings import Settings, get_settings


@dataclass
class ChatMessage:
    role: str
    content: str


class OpenAICompatibleLLM:
    """Small OpenAI-compatible client for DashScope/Qwen style endpoints."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def chat(self, messages: list[ChatMessage], model: str | None = None, timeout: int = 60) -> str:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is empty. Keep local fallback or configure DashScope first.")
        base_url = self.settings.openai_api_base.rstrip("/")
        if not base_url:
            raise RuntimeError("OPENAI_API_BASE is empty.")

        payload = {
            "model": model or self.settings.llm_model,
            "messages": [message.__dict__ for message in messages],
            "temperature": 0.1,
        }
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc
        return data["choices"][0]["message"]["content"]


def get_llm_client(settings: Settings | None = None) -> OpenAICompatibleLLM:
    return OpenAICompatibleLLM(settings)

