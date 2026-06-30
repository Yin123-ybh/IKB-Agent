from __future__ import annotations

import re
from pathlib import Path

from .base import BasePipelineNode
from ..state import ImportState
from ...utils.llm_utils import ChatMessage, get_llm_client


class MarkdownImageNode(BasePipelineNode):
    """Add semantic alt text for Markdown images.

    The production version can call Qwen3-VL-Flash and upload image assets to
    MinIO. The local implementation keeps tests offline and deterministic.
    """

    name = "md_image_node"
    _image_re = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)")

    def process(self, state: ImportState) -> ImportState:
        content = state.get("md_content", "")

        def replace(match: re.Match[str]) -> str:
            alt = match.group("alt").strip()
            path = match.group("path").strip()
            image_name = Path(path).name
            if alt:
                return match.group(0)
            title = self._nearby_heading(content, match.start())
            summary = self._summarize_image_reference(title, image_name)
            return f"![{summary}]({path})"

        state["md_content"] = self._image_re.sub(replace, content)
        return state

    def _summarize_image_reference(self, title: str, image_name: str) -> str:
        fallback = f"{title} related image: {image_name}" if title else f"Document image: {image_name}"
        if not self.settings.enable_external_llm:
            return fallback
        prompt = (
            "你是文档图片语义增强节点。当前只能看到图片文件名和附近标题，请生成一句适合写入 Markdown alt 的中文语义描述。"
            "不要编造具体看不见的细节，控制在 40 字以内。\n\n"
            f"附近标题：{title or '无'}\n图片文件名：{image_name}"
        )
        try:
            result = get_llm_client(self.settings).chat(
                [
                    ChatMessage(role="system", content="你负责生成简短、克制的图片语义描述。"),
                    ChatMessage(role="user", content=prompt),
                ],
                model=self.settings.vl_model,
                timeout=30,
            ).strip()
        except Exception:
            return fallback
        return result[:80] or fallback

    @staticmethod
    def _nearby_heading(content: str, position: int) -> str:
        before = content[:position].splitlines()
        for line in reversed(before):
            if re.match(r"^\s*#{1,6}\s+", line):
                return line.lstrip("#").strip()
        return ""
