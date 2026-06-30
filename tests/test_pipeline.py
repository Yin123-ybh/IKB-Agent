from pathlib import Path
from types import ModuleType

from ikb_agent.pipeline.nodes import DocumentSplitNode, ItemNameRecognitionNode, PdfToMarkdownNode
from ikb_agent.settings import Settings
from ikb_agent.storage import JsonKnowledgeStore
from ikb_agent.models import ChunkRecord, DocumentRecord, ImportTaskRecord, QueryRequest
from ikb_agent.services.query_service import QueryService
from ikb_agent.text_utils import sparse_vectorize, vectorize
from ikb_agent.utils import embedding_utils


def test_document_split_keeps_heading_context(tmp_path: Path):
    settings = Settings(data_dir=tmp_path, max_chunk_chars=120, min_chunk_chars=20)
    node = DocumentSplitNode(settings)
    state = {
        "file_title": "RS-12",
        "md_content": "# RS-12\n\n## 直流电压测量\n\n第一步，将旋钮拨到 V= 档。第二步，读取屏幕数值。\n\n## 注意事项\n\n禁止电流档测电压。",
    }

    result = node(state)

    assert result["chunks"]
    assert any("旋钮拨到 V= 档" in chunk["content"] for chunk in result["chunks"])
    assert all(chunk["title"] for chunk in result["chunks"])


def test_item_name_recognition_tags_all_chunks(tmp_path: Path):
    settings = Settings(data_dir=tmp_path)
    node = ItemNameRecognitionNode(settings)
    state = {
        "file_title": "万用表RS-12的使用",
        "chunks": [
            {"content": "# RS-12 数字万用表\n\n产品介绍", "title": "# RS-12 数字万用表"},
            {"content": "## 测量步骤\n\n将旋钮拨到 V= 档", "title": "## 测量步骤"},
        ],
    }

    result = node(state)

    assert "RS-12" in result["item_name"]
    assert all(chunk["item_name"] == result["item_name"] for chunk in result["chunks"])


def test_store_tracks_import_tasks(tmp_path: Path):
    store = JsonKnowledgeStore(tmp_path / "store.json")
    task = ImportTaskRecord(task_id="task-1", file_name="demo.md", status="processing", progress=10)

    store.upsert_task(task)
    completed = store.update_task("task-1", status="completed", progress=100, trace=["entry_node"])

    assert completed.status == "completed"
    assert completed.progress == 100
    assert store.get_task("task-1").trace == ["entry_node"]


def test_pdf_parse_mode_pypdf_skips_mineru_even_when_default_is_mineru(tmp_path: Path, monkeypatch):
    settings = Settings(data_dir=tmp_path, pdf_parse_backend="mineru")
    node = PdfToMarkdownNode(settings)
    pdf_path = tmp_path / "demo.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("MinerU should not be called when parse_mode is pypdf")

    monkeypatch.setattr(node, "_parse_with_mineru", fail_if_called)

    result = node(
        {
            "pdf_path": str(pdf_path),
            "file_dir": str(tmp_path / "processed"),
            "document_id": "doc-pypdf",
            "parse_mode": "pypdf",
            "warnings": [],
        }
    )

    assert Path(result["md_path"]).exists()
    assert result["is_md_read_enabled"] is True


def test_pdf_parse_mode_mineru_overrides_pypdf_default(tmp_path: Path, monkeypatch):
    settings = Settings(data_dir=tmp_path, pdf_parse_backend="pypdf")
    node = PdfToMarkdownNode(settings)
    pdf_path = tmp_path / "demo.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    mineru_md = tmp_path / "mineru.md"
    mineru_md.write_text("# MinerU result", encoding="utf-8")

    def fake_mineru(*args, **kwargs):
        return mineru_md

    monkeypatch.setattr(node, "_parse_with_mineru", fake_mineru)

    result = node(
        {
            "pdf_path": str(pdf_path),
            "file_dir": str(tmp_path / "processed"),
            "document_id": "doc-mineru",
            "parse_mode": "minneru",
            "warnings": [],
        }
    )

    assert result["md_path"] == str(mineru_md)
    assert result["is_md_read_enabled"] is True


def test_bge_m3_embedding_client_parses_dense_and_sparse(monkeypatch):
    class FakeBgeM3FlagModel:
        def __init__(self, *args, **kwargs):
            pass

        def encode(self, texts, **kwargs):
            return {
                "dense_vecs": [[0.1, 0.2], [0.3, 0.4]],
                "lexical_weights": [{"101": 0.7}, {"202": 0.9}],
            }

    fake_module = ModuleType("FlagEmbedding")
    fake_module.BGEM3FlagModel = FakeBgeM3FlagModel
    monkeypatch.setitem(__import__("sys").modules, "FlagEmbedding", fake_module)
    embedding_utils._get_cached_bge_client.cache_clear()

    client = embedding_utils.get_embedding_client(Settings(embedding_model="bge-m3", bge_device="cpu"))
    results = client.embed_documents(["hello", "world"])

    assert results[0].dense_vector == [0.1, 0.2]
    assert results[0].sparse_vector == {"101": 0.7}
    assert results[1].dense_vector == [0.3, 0.4]
    assert results[1].sparse_vector == {"202": 0.9}


def test_query_auto_item_name_does_not_hard_filter_results(tmp_path: Path):
    store = JsonKnowledgeStore(tmp_path / "store.json")
    docs = [
        DocumentRecord(
            document_id="rs",
            file_name="rs.md",
            file_title="RS-12数字万用表",
            item_name="RS-12",
            chunk_count=1,
        ),
        DocumentRecord(
            document_id="java",
            file_name="java.md",
            file_title="Java并发编程的艺术",
            item_name="Java并发编程的艺术",
            chunk_count=1,
        ),
    ]
    chunks = [
        ChunkRecord(
            chunk_id="rs-1",
            document_id="rs",
            title="RS-12",
            parent_title="RS-12",
            file_title="RS-12数字万用表",
            item_name="RS-12",
            content="RS-12 数字万用表用于直流电压测量。",
            dense_vector=vectorize("RS-12 数字万用表用于直流电压测量。"),
            sparse_vector=sparse_vectorize("RS-12 数字万用表用于直流电压测量。"),
        ),
        ChunkRecord(
            chunk_id="java-1",
            document_id="java",
            title="volatile 原理",
            parent_title="Java并发编程的艺术",
            file_title="Java并发编程的艺术",
            item_name="Java并发编程的艺术",
            content="Java 并发编程中的 volatile 通过内存屏障保证可见性。",
            dense_vector=vectorize("Java 并发编程中的 volatile 通过内存屏障保证可见性。"),
            sparse_vector=sparse_vectorize("Java 并发编程中的 volatile 通过内存屏障保证可见性。"),
        ),
    ]
    for doc in docs:
        store.upsert_document(doc, [chunk for chunk in chunks if chunk.document_id == doc.document_id])

    response = QueryService(store).query(QueryRequest(query="RS-12 和 Java volatile 都是什么？", top_k=2))

    assert response.item_names == ["RS-12"]
    assert {hit.document_id for hit in response.hits} == {"rs", "java"}
