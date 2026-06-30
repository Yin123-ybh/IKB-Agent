from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import ImportTaskRecord, QueryRequest, QueryResponse
from .pipeline import run_import
from .settings import get_settings
from .storage import JsonKnowledgeStore
from .text_utils import guess_item_name, strip_markdown

settings = get_settings()
store = JsonKnowledgeStore(settings.store_path)

app = FastAPI(
    title="IKB-Agent",
    description="Enterprise RAG document processing and retrieval platform.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "store": str(settings.store_path),
        "mode": "local-json-store",
    }


@app.get("/api/documents")
def documents() -> dict:
    return {"documents": [document.model_dump() for document in store.list_documents()]}


@app.get("/api/tasks")
def tasks() -> dict:
    return {"tasks": [task.model_dump() for task in store.list_tasks()]}


@app.get("/api/tasks/{task_id}")
def task_detail(task_id: str) -> dict:
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump()


@app.post("/api/import")
async def import_document(file: UploadFile = File(...)):
    original_name = Path(file.filename or "document.md").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".pdf", ".md", ".markdown", ".txt"}:
        raise HTTPException(status_code=400, detail="Only PDF, Markdown, and TXT files are supported.")

    task_id = uuid4().hex[:12]
    task = ImportTaskRecord(
        task_id=task_id,
        file_name=original_name,
        status="processing",
        progress=10,
        message="Document import started",
    )
    store.upsert_task(task)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / original_name
            temp_path.write_bytes(await file.read())
            response = run_import(temp_path, store, settings, document_id=task_id)
        completed = store.update_task(
            task_id,
            status="completed",
            progress=100,
            message="Document imported successfully",
            trace=response.trace,
            document_id=response.document.document_id,
        )
        response.task = completed
        return response.model_dump()
    except Exception as exc:
        store.update_task(
            task_id,
            status="failed",
            progress=100,
            message=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/demo-import")
def demo_import():
    task_id = uuid4().hex[:12]
    sample_path = settings.data_dir / "RS-12数字万用表.md"
    sample_path.write_text(
        """# RS-12 数字万用表使用说明

## 产品介绍
RS-12 数字万用表支持直流电压、交流电压、电阻和通断测量，适合门店售后排障和实验室基础测量。

## 直流电压测量
将黑表笔插入 COM 端口，红表笔插入 VΩ 端口。旋钮切换到 V= 档位后，将表笔并联到被测电路两端，读取屏幕数值。

## 电阻测量
测量电阻前应断开电路电源，并释放电容残余电荷。将旋钮切换到 Ω 档位，两支表笔分别接触电阻两端。

## 安全注意事项
测量高压前确认量程和表笔位置，禁止在电流档直接测量电压，避免烧毁保险丝或损坏设备。
""",
        encoding="utf-8",
    )
    store.upsert_task(
        ImportTaskRecord(
            task_id=task_id,
            file_name=sample_path.name,
            status="processing",
            progress=10,
            message="Demo import started",
        )
    )
    response = run_import(sample_path, store, settings, document_id=task_id)
    response.task = store.update_task(
        task_id,
        status="completed",
        progress=100,
        message="Demo document imported successfully",
        trace=response.trace,
        document_id=response.document.document_id,
    )
    return response.model_dump()


@app.post("/api/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    item_names = request.item_names
    if not item_names:
        inferred = guess_item_name("", request.query)
        item_names = [] if inferred == "未知商品" else [inferred]

    hits = store.search(request.query, top_k=request.top_k, item_names=item_names)
    if not hits and item_names:
        hits = store.search(request.query, top_k=request.top_k, item_names=[])

    answer = _build_answer(request.query, hits)
    return QueryResponse(
        answer=answer,
        hits=hits,
        rewritten_query=request.query.strip(),
        item_names=item_names,
    )


def _build_answer(query: str, hits) -> str:
    if not hits:
        return "暂未检索到足够相关的知识片段。请先导入文档，或换一个更具体的商品名/问题。"

    top = hits[0]
    evidence = strip_markdown(top.content, limit=520)
    bullet_lines = []
    for index, hit in enumerate(hits[:3], start=1):
        bullet_lines.append(
            f"{index}. {hit.title}（{hit.file_title} / {hit.item_name}，score={hit.score:.3f}）"
        )
    return (
        f"根据已导入知识库，问题「{query.strip()}」最相关的资料来自「{top.title}」。\n\n"
        f"核心依据：{evidence}\n\n"
        "召回来源：\n" + "\n".join(bullet_lines)
    )
