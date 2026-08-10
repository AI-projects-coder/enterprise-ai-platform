import asyncio
import os
import uuid
from datetime import timedelta

GCS_BUCKET = os.environ.get("GCS_BUCKET")
LOCAL_STORAGE_DIR = "/app/local_storage"

_gcs_client = None
_signing_credentials = None


def _get_gcs_client():
    global _gcs_client
    if _gcs_client is None:
        from google.cloud import storage as gcs_storage

        _gcs_client = gcs_storage.Client()
    return _gcs_client


def _get_signing_credentials():
    """Cloud Run's ADC identity only ever carries a short-lived access
    token, never an actual private key file — so blob.generate_signed_url()'s
    DEFAULT signing path (local, private-key-based) always fails there with
    "you need a private key to sign credentials" (hit live in sandbox: the
    serviceAccountTokenCreator role alone doesn't change this — it only
    unlocks a DIFFERENT signing path, and the code has to explicitly ask
    for it). Passing service_account_email + access_token to
    generate_signed_url switches it to remote signing via the IAM
    Credentials API's signBlob instead, which is exactly what that role
    grants permission to do. Not reached locally — both callers below are
    already gated behind `if not GCS_BUCKET: return None`."""
    global _signing_credentials
    import google.auth
    import google.auth.transport.requests

    if _signing_credentials is None:
        _signing_credentials, _ = google.auth.default()
    if not _signing_credentials.valid:
        _signing_credentials.refresh(google.auth.transport.requests.Request())
    return _signing_credentials


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
    datasets became the second thing besides video needing blob storage.
    Note: this plain read/write path never needed signing at all — it's
    only presigned_upload_url/presigned_read_url below (and therefore
    _get_signing_credentials) that ran into the private-key issue."""
    return await asyncio.to_thread(_save_sync, key, content, content_type, folder)


async def load(storage_ref: str) -> bytes:
    return await asyncio.to_thread(_load_sync, storage_ref)


def _presigned_upload_url_sync(key: uuid.UUID, folder: str, content_type: str) -> str | None:
    if not GCS_BUCKET:
        return None
    credentials = _get_signing_credentials()
    blob = _get_gcs_client().bucket(GCS_BUCKET).blob(f"{folder}/{key}")
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=15),
        method="PUT",
        content_type=content_type,
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )


def _presigned_read_url_sync(storage_ref: str) -> str | None:
    if not storage_ref.startswith("gs://"):
        return None
    credentials = _get_signing_credentials()
    _, _, rest = storage_ref.partition("gs://")
    bucket_name, _, blob_name = rest.partition("/")
    blob = _get_gcs_client().bucket(bucket_name).blob(blob_name)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=60),
        method="GET",
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )


async def presigned_upload_url(key: uuid.UUID, content_type: str, folder: str) -> str | None:
    """A short-lived signed PUT URL the browser can upload straight to GCS
    with — bytes never pass through this API's memory or Cloud Run's request
    limits, which is what made the old 20MB video cap necessary in the first
    place. Returns None when GCS isn't configured (local dev without GCP
    creds mounted in), signaling the caller to fall back to a direct
    multipart upload through the API instead — same environment split `save`
    already makes.

    Requires the calling service account to hold roles/iam.serviceAccount
    TokenCreator on its own identity (separate from ordinary storage
    read/write access) — see _get_signing_credentials for why, and why that
    role alone wasn't sufficient without also passing service_account_email/
    access_token here."""
    return await asyncio.to_thread(_presigned_upload_url_sync, key, folder, content_type)


async def presigned_read_url(storage_ref: str) -> str | None:
    """Signed GET URL for playback, valid 1 hour. Returns None for local-disk
    refs — those have no object store to sign against, so the caller serves
    them through its own streaming endpoint instead."""
    return await asyncio.to_thread(_presigned_read_url_sync, storage_ref)
