from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent
FRONTEND_ROOT = PACKAGE_ROOT / "static"
DATA_ROOT = PROJECT_ROOT / "data"
DOCS_ROOT = PROJECT_ROOT / "docs"

