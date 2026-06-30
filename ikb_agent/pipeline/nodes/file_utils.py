from __future__ import annotations

import re
import shutil
from pathlib import Path


def copy_to_upload_dir(source: Path, upload_dir: Path, document_id: str) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "-", source.stem).strip("-") or "document"
    target = upload_dir / f"{document_id}-{safe_stem}{source.suffix.lower()}"
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target

