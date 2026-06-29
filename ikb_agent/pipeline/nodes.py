from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from ..models import ChunkRecord, DocumentRecord
from ..settings import Settings
from ..storage import JsonKnowledgeStore
from ..text_utils import guess_item_name, sparse_vectorize, strip_markdown, vectorize
from .state import ImportState


class BasePipelineNode:
    name = "base_node"

    def __init__(self, settings: Settings):
        self.settings = settings

    def __call__(self, state: ImportState) -> ImportState:
        trace = list(state.get("trace", []))
        trace.append(self.name)
        state["trace"] = trace
        return self.process(state)

    def process(self, state: ImportState) -> ImportState:
        raise NotImplementedError


class EntryNode(BasePipelineNode):
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


class PdfToMarkdownNode(BasePipelineNode):
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


class MarkdownLoadNode(BasePipelineNode):
    name = "markdown_load_node"

    def process(self, state: ImportState) -> ImportState:
        md_path = Path(state["md_path"])
        content = md_path.read_text(encoding="utf-8", errors="ignore")
        if md_path.suffix.lower() == ".txt":
            content = f"# {md_path.stem}\n\n{content}"
        state["md_content"] = content
        return state


class MarkdownImageNode(BasePipelineNode):
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


class DocumentSplitNode(BasePipelineNode):
    name = "document_split_node"
    _heading_re = re.compile(r"^\s*(#{1,6})\s+(.+)")
    _fence_re = re.compile(r"^\s*(```|~~~)")

    def process(self, state: ImportState) -> ImportState:
        md_content = state.get("md_content", "").replace("\r\n", "\n").replace("\r", "\n")
        sections = self._split_by_headings(md_content, state.get("file_title", "document"))
        sections = self._split_and_merge(sections)
        state["chunks"] = self._assemble_chunks(sections)
        return state

    def _split_by_headings(self, content: str, file_title: str) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        hierarchy = [""] * 7
        body_lines: list[str] = []
        current_title = ""
        current_level = 0
        in_fence = False

        def flush() -> None:
            nonlocal body_lines
            body = "\n".join(body_lines).strip()
            title = current_title.strip() or file_title
            if not body and not current_title:
                return
            parent = ""
            for level in range(current_level - 1, 0, -1):
                if hierarchy[level]:
                    parent = hierarchy[level]
                    break
            sections.append(
                {
                    "title": title,
                    "body": body,
                    "parent_title": parent or title,
                    "file_title": file_title,
                }
            )

        for line in content.split("\n"):
            if self._fence_re.match(line):
                in_fence = not in_fence
            match = self._heading_re.match(line) if not in_fence else None
            if match:
                flush()
                current_title = line.strip()
                body_lines = []
                current_level = len(match.group(1))
                hierarchy[current_level] = current_title
                for level in range(current_level + 1, 7):
                    hierarchy[level] = ""
            else:
                body_lines.append(line)

        flush()
        if not sections and content.strip():
            sections.append(
                {
                    "title": file_title,
                    "body": content.strip(),
                    "parent_title": file_title,
                    "file_title": file_title,
                }
            )
        return sections

    def _split_and_merge(self, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        expanded: list[dict[str, Any]] = []
        for section in sections:
            expanded.extend(self._split_long_section(section))
        return self._merge_short_sections(expanded)

    def _split_long_section(self, section: dict[str, Any]) -> list[dict[str, Any]]:
        title = section["title"][:100]
        body = self._linearize_tables(section.get("body", ""))
        max_body_chars = max(self.settings.max_chunk_chars - len(title) - 2, 240)
        if len(title) + len(body) + 2 <= self.settings.max_chunk_chars:
            section["body"] = body
            return [section]

        parts = self._recursive_split(body, max_body_chars)
        return [
            {
                "title": f"{title} - {index + 1}",
                "body": part,
                "parent_title": section["parent_title"],
                "file_title": section["file_title"],
                "part": index + 1,
            }
            for index, part in enumerate(parts)
            if part.strip()
        ]

    def _merge_short_sections(self, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not sections:
            return []
        current = dict(sections[0])
        merged: list[dict[str, Any]] = []

        for next_section in sections[1:]:
            same_parent = current.get("parent_title") == next_section.get("parent_title")
            current_short = len(current.get("body", "")) < self.settings.min_chunk_chars
            combined_len = len(current.get("body", "")) + len(next_section.get("body", "")) + len(current.get("title", ""))
            if same_parent and current_short and combined_len <= self.settings.max_chunk_chars:
                current["body"] = f"{current.get('body', '').rstrip()}\n\n{next_section.get('body', '').lstrip()}".strip()
                current["title"] = current.get("parent_title") or current.get("title")
            else:
                merged.append(current)
                current = dict(next_section)

        merged.append(current)
        return merged

    @staticmethod
    def _recursive_split(text: str, max_chars: int) -> list[str]:
        separators = ["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " ", ""]

        def split_with(sep_index: int, value: str) -> list[str]:
            if len(value) <= max_chars:
                return [value.strip()]
            sep = separators[sep_index]
            if sep == "":
                return [value[i : i + max_chars].strip() for i in range(0, len(value), max_chars)]
            raw_parts = value.split(sep)
            parts = [part + sep for part in raw_parts[:-1]] + [raw_parts[-1]]
            chunks: list[str] = []
            bucket = ""
            for part in parts:
                if len(part) > max_chars and sep_index + 1 < len(separators):
                    if bucket:
                        chunks.append(bucket.strip())
                        bucket = ""
                    chunks.extend(split_with(sep_index + 1, part))
                elif len(bucket) + len(part) <= max_chars:
                    bucket += part
                else:
                    if bucket:
                        chunks.append(bucket.strip())
                    bucket = part
            if bucket:
                chunks.append(bucket.strip())
            return chunks

        return [part for part in split_with(0, text) if part]

    @staticmethod
    def _linearize_tables(text: str) -> str:
        return re.sub(r"</?(table|tr|td|th)[^>]*>", " | ", text, flags=re.I)

    @staticmethod
    def _assemble_chunks(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chunks = []
        for index, section in enumerate(sections, start=1):
            title = section.get("title", "").strip()
            body = section.get("body", "").strip()
            chunks.append(
                {
                    "chunk_index": index,
                    "title": title,
                    "parent_title": section.get("parent_title", title),
                    "file_title": section.get("file_title", ""),
                    "content": f"{title}\n\n{body}".strip(),
                }
            )
        return chunks


class ItemNameRecognitionNode(BasePipelineNode):
    name = "item_name_recognition_node"

    def process(self, state: ImportState) -> ImportState:
        chunks = state.get("chunks", [])
        context = self._prepare_context(chunks)
        item_name = guess_item_name(state.get("file_title", ""), context)
        state["item_name"] = item_name
        for chunk in chunks:
            chunk["item_name"] = item_name
        state["chunks"] = chunks
        return state

    def _prepare_context(self, chunks: list[dict[str, Any]]) -> str:
        pieces: list[str] = []
        total = 0
        for index, chunk in enumerate(chunks[: self.settings.item_name_chunk_k], start=1):
            content = chunk.get("content", "")
            piece = f"【切片】-{index}-{content}"
            if total + len(piece) > self.settings.item_name_context_chars and pieces:
                break
            pieces.append(piece)
            total += len(piece)
        return "\n".join(pieces)


class EmbeddingNode(BasePipelineNode):
    name = "bge_embedding_chunks_node"

    def process(self, state: ImportState) -> ImportState:
        for chunk in state.get("chunks", []):
            embedding_text = f"{chunk.get('item_name', '')}\n{chunk.get('content', '')}"
            chunk["dense_vector"] = vectorize(embedding_text)
            chunk["sparse_vector"] = sparse_vectorize(embedding_text)
        return state


class ImportStoreNode(BasePipelineNode):
    name = "milvus_import_node"

    def __init__(self, settings: Settings, store: JsonKnowledgeStore):
        super().__init__(settings)
        self.store = store

    def process(self, state: ImportState) -> ImportState:
        chunks: list[ChunkRecord] = []
        for chunk in state.get("chunks", []):
            chunk_id = f"{state['document_id']}-{chunk['chunk_index']:04d}"
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    document_id=state["document_id"],
                    content=chunk["content"],
                    title=chunk["title"],
                    parent_title=chunk["parent_title"],
                    file_title=chunk["file_title"],
                    item_name=chunk["item_name"],
                    dense_vector=chunk["dense_vector"],
                    sparse_vector=chunk["sparse_vector"],
                    metadata={"chunk_index": chunk["chunk_index"]},
                )
            )

        document = DocumentRecord(
            document_id=state["document_id"],
            file_name=Path(state["import_file_path"]).name,
            file_title=state["file_title"],
            item_name=state.get("item_name", state["file_title"]),
            chunk_count=len(chunks),
        )
        self.store.upsert_document(document, chunks)
        state["document"] = document.model_dump()
        state["chunk_records"] = [chunk.model_dump() for chunk in chunks]
        return state


def copy_to_upload_dir(source: Path, upload_dir: Path, document_id: str) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "-", source.stem).strip("-") or "document"
    target = upload_dir / f"{document_id}-{safe_stem}{source.suffix.lower()}"
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target
