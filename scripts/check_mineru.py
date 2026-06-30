from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ikb_agent.settings import get_settings


def main() -> None:
    settings = get_settings()
    print(f"python={sys.version.split()[0]}")
    print(f"PDF_PARSE_BACKEND={settings.pdf_parse_backend}")
    print(f"MINERU_CLI={settings.mineru_cli}")
    if sys.version_info >= (3, 14):
        print("[FAIL] MinerU dependencies usually do not support Python 3.14 yet. Use Python 3.10-3.13.")
    else:
        print("[ OK ] Python version is suitable for MinerU.")

    command = shutil.which(settings.mineru_cli) or shutil.which("magic-pdf")
    if not command:
        print("[FAIL] MinerU CLI not found. Install with: pip install -e '.[mineru]'")
        return
    print(f"[ OK ] MinerU CLI found: {command}")
    try:
        result = subprocess.run([command, "--help"], capture_output=True, text=True, timeout=20)
    except Exception as exc:
        print(f"[FAIL] MinerU CLI check failed: {exc}")
        return
    print("[ OK ] MinerU CLI is executable" if result.returncode == 0 else "[WARN] MinerU CLI returned non-zero for --help")


if __name__ == "__main__":
    main()
