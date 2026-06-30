from __future__ import annotations

import re
from pathlib import Path

from .base import BasePipelineNode
from ..state import ImportState


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
            summary = f"{title} related image: {image_name}" if title else f"Document image: {image_name}"
            return f"![{summary}]({path})"

        state["md_content"] = self._image_re.sub(replace, content)
        return state

    @staticmethod
    def _nearby_heading(content: str, position: int) -> str:
        before = content[:position].splitlines()
        for line in reversed(before):
            if re.match(r"^\s*#{1,6}\s+", line):
                return line.lstrip("#").strip()
        return ""

