"""HTTP session with retries and exponential backoff."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ingestion.common import config


def get_session() -> requests.Session:
    retry = Retry(
        total=5,
        backoff_factor=2,  # 2s, 4s, 8s, 16s, 32s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": config.USER_AGENT})
    return session
