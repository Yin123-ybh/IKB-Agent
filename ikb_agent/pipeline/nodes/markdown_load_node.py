from __future__ import annotations

from pathlib import Path

from .base import BasePipelineNode
from ..state import ImportState


class MarkdownLoadNode(BasePipelineNode):
    """Load Markdown or wrap TXT content as Markdown."""

    name = "markdown_load_node"

    def process(self, state: ImportState) -> ImportState:
        md_path = Path(state["md_path"])
        content = md_path.read_text(encoding="utf-8", errors="ignore")
        if md_path.suffix.lower() == ".txt":
            content = f"# {md_path.stem}\n\n{content}"
        state["md_content"] = content
        return state

