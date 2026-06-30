from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .base import BasePipelineNode
from ..state import ImportState


class PdfToMarkdownNode(BasePipelineNode):
    """Convert PDF to Markdown.

    Production mode uses MinerU to recover headings, tables, and image assets.
    Local mode can still use pypdf as a lightweight fallback.
    """

    name = "pdf_to_md_node"

    def process(self, state: ImportState) -> ImportState:
        pdf_path = Path(state["pdf_path"])
        output_dir = Path(state["file_dir"]) / state["document_id"]
        output_dir.mkdir(parents=True, exist_ok=True)
        md_path = output_dir / f"{pdf_path.stem}.md"
        warnings = state.setdefault("warnings", [])

        if self.settings.pdf_parse_backend in {"mineru", "auto"}:
            mineru_md = self._parse_with_mineru(pdf_path, output_dir, warnings)
            if mineru_md:
                state["md_path"] = str(mineru_md)
                state["is_md_read_enabled"] = True
                return state
            if self.settings.pdf_parse_backend == "mineru":
                raise RuntimeError("MinerU parsing failed. Check MINERU_CLI, Python version, and model configuration.")

        pages: list[str] = []
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

    def _parse_with_mineru(self, pdf_path: Path, output_dir: Path, warnings: list[str]) -> Path | None:
        command = self._resolve_cli(self.settings.mineru_cli)
        if not command and self.settings.mineru_cli == "mineru":
            command = self._resolve_cli("magic-pdf")
        if not command:
            warnings.append("MinerU CLI not found. Install MinerU or set MINERU_CLI.")
            return None

        mineru_output_dir = output_dir / "mineru"
        mineru_output_dir.mkdir(parents=True, exist_ok=True)
        base_command = [
            command,
            "-p",
            str(pdf_path),
            "-o",
            str(mineru_output_dir),
            "-m",
            self.settings.mineru_method,
            "-b",
            self.settings.mineru_backend,
            "-f",
            str(self.settings.mineru_formula).lower(),
            "-t",
            str(self.settings.mineru_table).lower(),
            "--image-analysis",
            str(self.settings.mineru_image_analysis).lower(),
        ]
        candidates = [
            base_command,
            [command, "-p", str(pdf_path), "-o", str(mineru_output_dir)],
        ]
        last_error = ""
        for candidate in candidates:
            try:
                result = subprocess.run(candidate, capture_output=True, text=True, timeout=900, check=False)
            except Exception as exc:
                last_error = str(exc)
                continue
            if result.returncode == 0:
                md_path = self._find_mineru_markdown(mineru_output_dir, pdf_path.stem)
                if md_path:
                    return md_path
                last_error = "MinerU completed but no Markdown file was found."
            else:
                last_error = self._compact_error(result.stderr or result.stdout or "")
        warnings.append(f"MinerU parsing failed: {last_error}")
        return None

    @staticmethod
    def _find_mineru_markdown(output_dir: Path, pdf_stem: str) -> Path | None:
        markdown_files = sorted(output_dir.rglob("*.md"), key=lambda path: (path.stem != pdf_stem, len(path.parts)))
        return markdown_files[0] if markdown_files else None

    @staticmethod
    def _resolve_cli(name: str) -> str | None:
        command = shutil.which(name)
        if command:
            return command
        sibling = Path(sys.executable).parent / name
        return str(sibling) if sibling.exists() else None

    @staticmethod
    def _compact_error(output: str) -> str:
        output = (output or "").strip()
        marker = "Error no file named"
        if marker in output:
            return output[output.rfind(marker) :].splitlines()[0]
        marker = "Error:"
        if marker in output:
            return output[output.rfind(marker) :].strip()[-1000:]
        return output[-1000:]
