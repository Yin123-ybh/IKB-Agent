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
        warnings = state.setdefault("warnings", [])
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf_path))
            for index, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"## Page {index}\n\n{text.strip()}")
        except ImportError:
            warnings.append("PDF text extraction skipped: install pypdf with `pip install -e '.[pdf]'`.")
        except Exception as exc:
            warnings.append(f"PDF text extraction failed: {exc}")
            pages = []

        if not pages:
            warnings.append("No readable PDF text was extracted. The document was stored with a parsing notice only.")
            pages.append(
                "## PDF Parsing Notice\n\n"
                "本地演示模式没有从这个 PDF 中抽取到可检索正文。"
                "请先安装 pypdf 后重新导入；如果这是扫描版或复杂版式 PDF，生产环境需要接入 MinerU 解析正文、表格和图片。"
            )

        md_path.write_text(f"# {pdf_path.stem}\n\n" + "\n\n".join(pages), encoding="utf-8")
        state["md_path"] = str(md_path)
        state["is_md_read_enabled"] = True
        return state
