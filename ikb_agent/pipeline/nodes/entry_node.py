from __future__ import annotations

import re
from pathlib import Path

from .base import BasePipelineNode
from ..state import ImportState


class EntryNode(BasePipelineNode):
    """Detect file type and initialize routing flags."""

    name = "entry_node"

    def process(self, state: ImportState) -> ImportState:
        source = Path(state["import_file_path"])
        suffix = source.suffix.lower()
        file_title = re.sub(r"^[0-9a-f]{12}-", "", source.stem)
        file_title = re.sub(r"-[0-9a-f]{12}$", "", file_title)
        state["file_title"] = file_title
        state["file_type"] = suffix.lstrip(".") or "txt"

        if suffix == ".pdf":
            state["is_pdf_read_enabled"] = True
            state["is_md_read_enabled"] = False
            state["pdf_path"] = str(source)
            return state

        if suffix in {".md", ".markdown", ".txt"}:
            state["is_pdf_read_enabled"] = False
            state["is_md_read_enabled"] = True
            state["md_path"] = str(source)
            return state

        raise ValueError(f"Unsupported file type: {suffix}. Please upload PDF, Markdown, or TXT.")

