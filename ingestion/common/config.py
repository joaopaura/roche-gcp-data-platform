"""Central configuration, read from environment variables / .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "roche-data-platform")
REGION = os.getenv("GCP_REGION", "us-central1")
LAKE_BUCKET = os.getenv("LAKE_BUCKET", "roche-data-platform-lake")

# Local runs impersonate the ingestion service account (keyless).
# In GitHub Actions this stays empty and Workload Identity is used instead.
IMPERSONATE_SA = os.getenv("IMPERSONATE_SA", "")

OPENFDA_API_KEY = os.getenv("OPENFDA_API_KEY", "")

RAW_DATASET = "raw"
OPS_DATASET = "ops"

USER_AGENT = (
    "Mozilla/5.0 (compatible; roche-gcp-data-platform/1.0; "
    "+https://github.com/joaopaura/roche-gcp-data-platform)"
)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
