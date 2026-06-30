from __future__ import annotations

from pathlib import Path

from ..settings import Settings, get_settings


class MinioResourceStore:
    """Original document and image storage adapter."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        try:
            from minio import Minio
        except ImportError as exc:
            raise RuntimeError("Install middleware dependencies first: pip install -e '.[middleware]'") from exc

        self.client = Minio(
            self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=self.settings.minio_secure,
        )

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.settings.minio_bucket_name):
            self.client.make_bucket(self.settings.minio_bucket_name)

    def upload_file(self, object_name: str, file_path: Path, content_type: str | None = None) -> str:
        self.ensure_bucket()
        self.client.fput_object(
            self.settings.minio_bucket_name,
            object_name,
            str(file_path),
            content_type=content_type,
        )
        return f"minio://{self.settings.minio_bucket_name}/{object_name}"

    def ping(self) -> bool:
        self.client.list_buckets()
        return True

