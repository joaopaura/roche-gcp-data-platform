"""Google Cloud Storage helpers for the data lake."""
from datetime import date
from pathlib import Path

from google.cloud import storage

from ingestion.common import config
from ingestion.common.auth import get_credentials

_client = None


def _bucket():
    global _client
    if _client is None:
        _client = storage.Client(project=config.PROJECT_ID, credentials=get_credentials())
    return _client.bucket(config.LAKE_BUCKET)


def lake_path(zone: str, source: str, *parts: str) -> str:
    """Build a lake path, e.g. raw/ecb_fx/ingest_date=2026-09-29/file.csv"""
    return "/".join([zone, source, *parts])


def today_partition() -> str:
    return f"ingest_date={date.today().isoformat()}"


def upload_file(local_path: Path, blob_name: str) -> str:
    blob = _bucket().blob(blob_name)
    blob.chunk_size = 16 * 1024 * 1024  # resumable upload in 16 MB chunks
    blob.upload_from_filename(str(local_path), timeout=900)
    return f"gs://{config.LAKE_BUCKET}/{blob_name}"


def upload_bytes(data: bytes, blob_name: str, content_type: str = "application/octet-stream") -> str:
    _bucket().blob(blob_name).upload_from_string(data, content_type=content_type, timeout=300)
    return f"gs://{config.LAKE_BUCKET}/{blob_name}"


def blob_exists(blob_name: str) -> bool:
    return _bucket().blob(blob_name).exists()


def gcs_uri(blob_name: str) -> str:
    return f"gs://{config.LAKE_BUCKET}/{blob_name}"


def download_file(blob_name: str, local_path: Path) -> Path:
    _bucket().blob(blob_name).download_to_filename(str(local_path), timeout=900)
    return local_path
