from __future__ import annotations

import re
from typing import Any

from .base import BasePipelineNode
from ..state import ImportState


class DocumentSplitNode(BasePipelineNode):
    """Split Markdown into retrieval-friendly chunks."""

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

