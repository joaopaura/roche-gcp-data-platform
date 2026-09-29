"""Google credentials: Application Default Credentials, optionally impersonating a service account."""
import google.auth
from google.auth import impersonated_credentials

from ingestion.common import config

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def get_credentials():
    source_credentials, _ = google.auth.default(scopes=SCOPES)
    if not config.IMPERSONATE_SA:
        return source_credentials
    return impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=config.IMPERSONATE_SA,
        target_scopes=SCOPES,
        lifetime=3600,
    )
