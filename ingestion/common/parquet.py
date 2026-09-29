"""Write a DataFrame to Parquet in a temp folder, upload it to the lake and return (uri, bytes)."""
import tempfile
from pathlib import Path

import pandas as pd

from ingestion.common import gcs


def upload_dataframe(df: pd.DataFrame, blob_name: str) -> tuple[str, int]:
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / "data.parquet"
        df.to_parquet(local, index=False, compression="snappy")
        size = local.stat().st_size
        uri = gcs.upload_file(local, blob_name)
    return uri, size
