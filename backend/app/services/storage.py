from __future__ import annotations

from functools import lru_cache
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings


class StorageServiceError(Exception):
    pass


@lru_cache
def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket_exists(bucket_name: str) -> None:
    client = get_minio_client()
    if client.bucket_exists(bucket_name):
        return

    try:
        client.make_bucket(bucket_name)
    except S3Error as exc:
        if exc.code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise StorageServiceError(f"Could not create MinIO bucket '{bucket_name}'.") from exc


def parse_storage_key(storage_key: str) -> tuple[str, str]:
    bucket_name, separator, object_name = storage_key.partition("/")
    if not bucket_name or not separator or not object_name:
        raise StorageServiceError("Document storage_key is not a valid MinIO path.")
    return bucket_name, object_name


def get_object_buffer(bucket_name: str, object_name: str) -> BytesIO:
    try:
        response = get_minio_client().get_object(bucket_name, object_name)
    except S3Error as exc:
        raise StorageServiceError("Could not download object from MinIO.") from exc

    try:
        return BytesIO(response.read())
    except S3Error as exc:
        raise StorageServiceError("Could not download object from MinIO.") from exc
    finally:
        response.close()
        response.release_conn()
