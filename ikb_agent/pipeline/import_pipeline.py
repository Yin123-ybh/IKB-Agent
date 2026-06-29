from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from langgraph.constants import END
from langgraph.graph import StateGraph

from ..models import ChunkRecord, DocumentRecord, ImportResponse
from ..settings import Settings, get_settings
from ..storage import JsonKnowledgeStore
from .nodes import (
    DocumentSplitNode,
    EmbeddingNode,
    EntryNode,
    ImportStoreNode,
    ItemNameRecognitionNode,
    MarkdownImageNode,
    MarkdownLoadNode,
    PdfToMarkdownNode,
    copy_to_upload_dir,
)
from .state import ImportState


def _route_after_entry(state: ImportState) -> str:
    if state.get("is_pdf_read_enabled"):
        return "pdf_to_md_node"
    if state.get("is_md_read_enabled"):
        return "markdown_load_node"
    return END


def build_import_graph(settings: Settings, store: JsonKnowledgeStore):
    graph = StateGraph(ImportState)
    graph.add_node("entry_node", EntryNode(settings))
    graph.add_node("pdf_to_md_node", PdfToMarkdownNode(settings))
    graph.add_node("markdown_load_node", MarkdownLoadNode(settings))
    graph.add_node("md_image_node", MarkdownImageNode(settings))
    graph.add_node("document_split_node", DocumentSplitNode(settings))
    graph.add_node("item_name_recognition_node", ItemNameRecognitionNode(settings))
    graph.add_node("bge_embedding_chunks_node", EmbeddingNode(settings))
    graph.add_node("milvus_import_node", ImportStoreNode(settings, store))

    graph.set_entry_point("entry_node")
    graph.add_conditional_edges(
        "entry_node",
        _route_after_entry,
        {
            "pdf_to_md_node": "pdf_to_md_node",
            "markdown_load_node": "markdown_load_node",
            END: END,
        },
    )
    graph.add_edge("pdf_to_md_node", "markdown_load_node")
    graph.add_edge("markdown_load_node", "md_image_node")
    graph.add_edge("md_image_node", "document_split_node")
    graph.add_edge("document_split_node", "item_name_recognition_node")
    graph.add_edge("item_name_recognition_node", "bge_embedding_chunks_node")
    graph.add_edge("bge_embedding_chunks_node", "milvus_import_node")
    graph.add_edge("milvus_import_node", END)
    return graph.compile()


def run_import(
    file_path: Path,
    store: JsonKnowledgeStore,
    settings: Settings | None = None,
    document_id: str | None = None,
) -> ImportResponse:
    settings = settings or get_settings()
    document_id = document_id or uuid4().hex[:12]
    staged_file = copy_to_upload_dir(file_path, settings.upload_dir, document_id)
    app = build_import_graph(settings, store)
    state: ImportState = {
        "trace": [],
        "document_id": document_id,
        "import_file_path": str(staged_file),
        "file_dir": str(settings.data_dir / "processed"),
    }
    result = app.invoke(state)
    return ImportResponse(
        message="Document imported successfully",
        document=DocumentRecord(**result["document"]),
        chunks=[ChunkRecord(**chunk) for chunk in result["chunk_records"]],
        trace=result.get("trace", []),
    )

