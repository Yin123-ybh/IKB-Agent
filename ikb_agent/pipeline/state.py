from __future__ import annotations

from typing import Any, TypedDict


class ImportState(TypedDict, total=False):
    trace: list[str]
    document_id: str
    import_file_path: str
    file_dir: str
    file_title: str
    file_type: str
    is_pdf_read_enabled: bool
    is_md_read_enabled: bool
    pdf_path: str
    md_path: str
    md_content: str
    chunks: list[dict[str, Any]]
    item_name: str
    warnings: list[str]
    document: dict[str, Any]
    chunk_records: list[dict[str, Any]]
