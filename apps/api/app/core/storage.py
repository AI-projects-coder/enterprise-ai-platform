import asyncio
import os
import uuid

GCS_BUCKET = os.environ.get("GCS_BUCKET")
LOCAL_STORAGE_DIR = "/app/local_storage"

_gcs_client = None


def _get_gcs_client():
    global _gcs_client
    if _gcs_client is None:
        from google.cloud import storage as gcs_storage

        _gcs_client = gcs_storage.Client()
    return _gcs_client


def _save_sync(key: uuid.UUID, content: bytes, content_type: str, folder: str) -> str:
    if GCS_BUCKET:
        blob = _get_gcs_client().bucket(GCS_BUCKET).blob(f"{folder}/{key}")
        blob.upload_from_string(content, content_type=content_type)
        return f"gs://{GCS_BUCKET}/{folder}/{key}"

    local_dir = os.path.join(LOCAL_STORAGE_DIR, folder)
    os.makedirs(local_dir, exist_ok=True)
    path = os.path.join(local_dir, str(key))
    with open(path, "wb") as f:
        f.write(content)
    return path


def _load_sync(storage_ref: str) -> bytes:
    if storage_ref.startswith("gs://"):
        _, _, rest = storage_ref.partition("gs://")
        bucket_name, _, blob_name = rest.partition("/")
        return _get_gcs_client().bucket(bucket_name).blob(blob_name).download_as_bytes()

    with open(storage_ref, "rb") as f:
        return f.read()


async def save(key: uuid.UUID, content: bytes, content_type: str, folder: str) -> str:
    """GCS in any environment where GCS_BUCKET is set (all deployed envs);
    local disk otherwise, so local dev needs no GCP credentials mounted in
    at all — same reasoning as why local Postgres is a plain Docker
    container instead of talking to a real Cloud SQL instance.
    google-cloud-storage's client is synchronous (blocking) — run it in a
    thread so it doesn't stall the event loop the rest of this app depends
    on being free (FastAPI + asyncpg are both async throughout).
    `folder` namespaces different content types (videos/, datasets/, ...)
    within the one shared bucket/local dir — introduced in phase 11 when
    datasets became the second thing besides video needing blob storage."""
    return await asyncio.to_thread(_save_sync, key, content, content_type, folder)


async def load(storage_ref: str) -> bytes:
    return await asyncio.to_thread(_load_sync, storage_ref)
