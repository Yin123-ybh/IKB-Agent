from __future__ import annotations

from pathlib import Path


def main() -> None:
    try:
        from modelscope import snapshot_download
    except ImportError as exc:
        raise SystemExit("Install modelscope first: pip install modelscope") from exc

    cache_dir = Path("models").resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_dir = snapshot_download(
        "BAAI/bge-m3",
        cache_dir=str(cache_dir),
        revision="master",
    )
    print("[ OK ] BGE-M3 downloaded")
    print(f"BGE_M3_PATH={model_dir}")
    print("Put this BGE_M3_PATH into your .env, then restart uvicorn.")


if __name__ == "__main__":
    main()
