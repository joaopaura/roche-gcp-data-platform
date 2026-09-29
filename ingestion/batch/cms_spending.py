"""CMS Medicare Part B and Part D Spending by Drug (real US spend) -> lake -> raw.cms_part_b / raw.cms_part_d

Files are wide (one column per year, e.g. Tot_Spndng_2023). They are kept as-is (all strings)
and unpivoted in dbt, so a new year added by CMS never breaks the load (schema drift).

Run:  python -m ingestion.batch.cms_spending
"""
import json

import pandas as pd

from ingestion.common import bq, gcs
from ingestion.common.http import get_session
from ingestion.common.logger import get_logger
from ingestion.common.parquet import upload_dataframe
from ingestion.common.run_tracker import track_run

SOURCE = "cms_spending"
API = "https://data.cms.gov/data-api/v1/dataset/{uuid}/data"
DATASETS = {
    "cms_part_d": "7e0b4365-fd63-4a29-8f5e-e0ac9f66a81b",  # Medicare Part D Spending by Drug
    "cms_part_b": "76a714ad-3a2c-43ac-b76d-9dadf8f7d890",  # Medicare Part B Spending by Drug
}
PAGE_SIZE = 5000

logger = get_logger(SOURCE)


def fetch_dataset(uuid: str) -> list[dict]:
    session = get_session()
    rows, offset = [], 0
    while True:
        response = session.get(API.format(uuid=uuid), params={"size": PAGE_SIZE, "offset": offset}, timeout=120)
        response.raise_for_status()
        page = response.json()
        rows.extend(page)
        logger.info("%s: %s rows", uuid, len(rows))
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


def main() -> None:
    with track_run(SOURCE) as run:
        for table, uuid in DATASETS.items():
            rows = fetch_dataset(uuid)
            raw_bytes = json.dumps(rows).encode("utf-8")
            gcs.upload_bytes(raw_bytes, gcs.lake_path("raw", SOURCE, gcs.today_partition(), f"{table}.json"), "application/json")

            df = pd.DataFrame(rows).astype("string")
            year_cols = sorted({c.rsplit("_", 1)[-1] for c in df.columns if c[-4:].isdigit()})
            logger.info("%s: %s rows, %s columns, years %s", table, len(df), len(df.columns), year_cols)

            uri, size = upload_dataframe(df, gcs.lake_path("bronze", SOURCE, f"{table}.parquet"))
            run["rows_loaded"] += bq.load_parquet(uri, table)
            run["files_written"] += 2
            run["bytes_written"] += len(raw_bytes) + size
        run["target"] = "raw.cms_part_b, raw.cms_part_d"


if __name__ == "__main__":
    main()
