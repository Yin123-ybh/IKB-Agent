from __future__ import annotations

import shutil
import shlex
import subprocess
import sys
import time
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
        parse_mode = self._normalize_parse_mode(state.get("parse_mode", self.settings.pdf_parse_backend))

        if parse_mode in {"mineru", "auto"}:
            mineru_md = self._parse_with_mineru(pdf_path, output_dir, warnings)
            if mineru_md:
                state["md_path"] = str(mineru_md)
                state["is_md_read_enabled"] = True
                return state
            if parse_mode == "mineru":
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
        if self.settings.mineru_source and self._cli_supports(command, "--source"):
            base_command.extend(["--source", self.settings.mineru_source])
        if self.settings.mineru_extra_args:
            base_command.extend(shlex.split(self.settings.mineru_extra_args))

        candidates = [
            base_command,
            [command, "-p", str(pdf_path), "-o", str(mineru_output_dir)],
        ]
        last_error = ""
        log_path = output_dir / "mineru.log"
        for candidate in candidates:
            return_code, output = self._run_mineru(candidate, log_path)
            if return_code == 0:
                md_path = self._find_mineru_markdown(mineru_output_dir, pdf_path.stem)
                if md_path:
                    return md_path
                last_error = "MinerU completed but no Markdown file was found."
            else:
                last_error = self._compact_error(output)
        warnings.append(f"MinerU parsing failed: {last_error}")
        return None

    @staticmethod
    def _normalize_parse_mode(value: str | None) -> str:
        mode = (value or "pypdf").strip().lower()
        aliases = {
            "light": "pypdf",
            "fast": "pypdf",
            "local": "pypdf",
            "minneru": "mineru",
        }
        return aliases.get(mode, mode if mode in {"pypdf", "mineru", "auto"} else "pypdf")

    @staticmethod
    def _run_mineru(command: list[str], log_path: Path) -> tuple[int, str]:
        start_time = time.time()
        output_lines: list[str] = []
        print(f"[MinerU] command: {shlex.join(command)}")
        try:
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"\n[MinerU] command: {shlex.join(command)}\n")
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )
                assert process.stdout is not None
                for line in process.stdout:
                    output_lines.append(line)
                    log_file.write(line)
                    log_file.flush()
                    print(f"[MinerU] {line.rstrip()}")
                return_code = process.wait(timeout=900)
                elapsed = time.time() - start_time
                log_file.write(f"[MinerU] exit={return_code}, elapsed={elapsed:.2f}s\n")
                print(f"[MinerU] exit={return_code}, elapsed={elapsed:.2f}s")
                return return_code, "".join(output_lines)
        except Exception as exc:
            return 1, str(exc)

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
    def _cli_supports(command: str, option: str) -> bool:
        try:
            result = subprocess.run([command, "--help"], capture_output=True, text=True, timeout=20, check=False)
        except Exception:
            return False
        return option in f"{result.stdout}\n{result.stderr}"

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
