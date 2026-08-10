import asyncio
import os
import uuid
from datetime import timedelta

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


def _presigned_upload_url_sync(key: uuid.UUID, folder: str, content_type: str) -> str | None:
    if not GCS_BUCKET:
        return None
    blob = _get_gcs_client().bucket(GCS_BUCKET).blob(f"{folder}/{key}")
    return blob.generate_signed_url(
        version="v4", expiration=timedelta(minutes=15), method="PUT", content_type=content_type
    )


def _presigned_read_url_sync(storage_ref: str) -> str | None:
    if not storage_ref.startswith("gs://"):
        return None
    _, _, rest = storage_ref.partition("gs://")
    bucket_name, _, blob_name = rest.partition("/")
    blob = _get_gcs_client().bucket(bucket_name).blob(blob_name)
    return blob.generate_signed_url(version="v4", expiration=timedelta(minutes=60), method="GET")


async def presigned_upload_url(key: uuid.UUID, content_type: str, folder: str) -> str | None:
    """A short-lived signed PUT URL the browser can upload straight to GCS
    with — bytes never pass through this API's memory or Cloud Run's request
    limits, which is what made the old 20MB video cap necessary in the first
    place. Returns None when GCS isn't configured (local dev without GCP
    creds mounted in), signaling the caller to fall back to a direct
    multipart upload through the API instead — same environment split `save`
    already makes.

    NOTE: signing requires the calling service account to be able to sign
    blobs itself (IAM Credentials API / roles/iam.serviceAccountTokenCreator
    on its own identity) when using ADC rather than a private key file — this
    is a real, separate permission from the storage access already granted,
    and needs to be verified live against the sandbox Cloud Run service
    account before this path is trusted in a deployed environment."""
    return await asyncio.to_thread(_presigned_upload_url_sync, key, folder, content_type)


async def presigned_read_url(storage_ref: str) -> str | None:
    """Signed GET URL for playback, valid 1 hour. Returns None for local-disk
    refs — those have no object store to sign against, so the caller serves
    them through its own streaming endpoint instead."""
    return await asyncio.to_thread(_presigned_read_url_sync, storage_ref)
