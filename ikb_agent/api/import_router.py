from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from ..core.deps import get_import_service
from ..services import ImportService

router = APIRouter(prefix="/api", tags=["import"])


@router.post("/import")
async def import_document(
    file: UploadFile = File(...),
    service: ImportService = Depends(get_import_service),
):
    with tempfile.TemporaryDirectory() as temp_dir:
        response = await service.import_upload(file, Path(temp_dir))
        return response.model_dump()


@router.post("/demo-import")
def demo_import(service: ImportService = Depends(get_import_service)):
    return service.import_demo().model_dump()
