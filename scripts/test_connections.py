from __future__ import annotations

import sys
import socket
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ikb_agent.settings import get_settings
from ikb_agent.utils.milvus_utils import MilvusVectorStore
from ikb_agent.utils.minio_utils import MinioResourceStore
from ikb_agent.utils.mongo_history_utils import MongoHistoryStore


def endpoint_host_port(endpoint: str, default_port: int) -> tuple[str, int]:
    parsed = urlparse(endpoint if "://" in endpoint else f"tcp://{endpoint}")
    host = parsed.hostname or "localhost"
    port = parsed.port or default_port
    return host, port


def tcp_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check(name: str, endpoint: str, default_port: int, factory) -> None:
    host, port = endpoint_host_port(endpoint, default_port)
    if not tcp_open(host, port):
        print(f"[FAIL] {name}: {host}:{port} is not reachable. Start docker compose first.")
        return
    try:
        ok = factory().ping()
    except Exception as exc:
        print(f"[FAIL] {name}: {exc}")
        return
    print(f"[ OK ] {name}: connected" if ok else f"[FAIL] {name}: ping returned false")


def main() -> None:
    settings = get_settings()
    print(f"DATA_DIR={settings.data_dir}")
    print(f"MILVUS_URL={settings.milvus_url}")
    print(f"MONGO_URL={settings.mongo_url}")
    print(f"MINIO_ENDPOINT={settings.minio_endpoint}")
    check("Milvus", settings.milvus_url, 19530, lambda: MilvusVectorStore(settings))
    check("MongoDB", settings.mongo_url, 27017, lambda: MongoHistoryStore(settings))
    check("MinIO", settings.minio_endpoint, 9000, lambda: MinioResourceStore(settings))


if __name__ == "__main__":
    main()
