from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from ..models import ImportResponse, ImportTaskRecord
from ..pipeline import run_import
from ..settings import Settings
from ..storage import JsonKnowledgeStore


class ImportService:
    """Application service for document import use cases."""

    supported_suffixes = {".pdf", ".md", ".markdown", ".txt"}

    def __init__(self, settings: Settings, store: JsonKnowledgeStore):
        self.settings = settings
        self.store = store

    async def import_upload(self, file: UploadFile, temp_dir: Path) -> ImportResponse:
        original_name = Path(file.filename or "document.md").name
        suffix = Path(original_name).suffix.lower()
        if suffix not in self.supported_suffixes:
            raise HTTPException(status_code=400, detail="Only PDF, Markdown, and TXT files are supported.")

        task_id = uuid4().hex[:12]
        self.store.upsert_task(
            ImportTaskRecord(
                task_id=task_id,
                file_name=original_name,
                status="processing",
                progress=10,
                message="Document import started",
            )
        )

        try:
            temp_path = temp_dir / original_name
            temp_path.write_bytes(await file.read())
            response = run_import(temp_path, self.store, self.settings, document_id=task_id)
            task_message = response.message
            response.task = self.store.update_task(
                task_id,
                status="completed",
                progress=100,
                message=task_message,
                trace=response.trace,
                document_id=response.document.document_id,
            )
            return response
        except Exception as exc:
            self.store.update_task(task_id, status="failed", progress=100, message=str(exc))
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    def import_demo(self) -> ImportResponse:
        task_id = uuid4().hex[:12]
        sample_path = self.settings.data_dir / "RS-12数字万用表.md"
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
        self.store.upsert_task(
            ImportTaskRecord(
                task_id=task_id,
                file_name=sample_path.name,
                status="processing",
                progress=10,
                message="Demo import started",
            )
        )
        response = run_import(sample_path, self.store, self.settings, document_id=task_id)
        response.task = self.store.update_task(
            task_id,
            status="completed",
            progress=100,
            message="Demo document imported successfully",
            trace=response.trace,
            document_id=response.document.document_id,
        )
        return response
