from __future__ import annotations

from pathlib import Path

from .base import BasePipelineNode
from ..state import ImportState


class PdfToMarkdownNode(BasePipelineNode):
    """Convert PDF to Markdown.

    Local mode tries pypdf when installed. Production mode can replace this
    node with MinerU while keeping the same state contract.
    """

    name = "pdf_to_md_node"

    def process(self, state: ImportState) -> ImportState:
        pdf_path = Path(state["pdf_path"])
        output_dir = Path(state["file_dir"]) / state["document_id"]
        output_dir.mkdir(parents=True, exist_ok=True)
        md_path = output_dir / f"{pdf_path.stem}.md"

        pages: list[str] = []
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf_path))
            for index, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"## Page {index}\n\n{text.strip()}")
        except Exception:
            pages = []

        if not pages:
            pages.append(
                "## PDF Parsing Notice\n\n"
                "The local demo could not extract text from this PDF. "
                "In production, configure MinerU to recover headings, tables, and images."
            )

        md_path.write_text(f"# {pdf_path.stem}\n\n" + "\n\n".join(pages), encoding="utf-8")
        state["md_path"] = str(md_path)
        state["is_md_read_enabled"] = True
        return state

