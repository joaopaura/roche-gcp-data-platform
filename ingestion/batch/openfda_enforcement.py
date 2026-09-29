"""openFDA drug enforcement (recalls) for Genentech / Roche -> lake -> raw.fda_recalls

Run:  python -m ingestion.batch.openfda_enforcement
"""
import json

import pandas as pd

from ingestion.common import bq, config, gcs
from ingestion.common.http import get_session
from ingestion.common.logger import get_logger
from ingestion.common.parquet import upload_dataframe
from ingestion.common.run_tracker import track_run

SOURCE = "openfda_enforcement"
URL = "https://api.fda.gov/drug/enforcement.json"
SEARCHES = ["recalling_firm:genentech", "recalling_firm:roche", "recalling_firm:hoffmann"]
PAGE_SIZE = 1000

FIELDS = [
    "recall_number", "event_id", "status", "classification", "product_type", "recalling_firm",
    "reason_for_recall", "product_description", "product_quantity", "distribution_pattern",
    "voluntary_mandated", "initial_firm_notification", "recall_initiation_date",
    "center_classification_date", "report_date", "termination_date", "city", "state", "country",
]

logger = get_logger(SOURCE)


def fetch_recalls(search: str) -> list[dict]:
    session = get_session()
    results, skip = [], 0
    while True:
        params = {"search": search, "limit": PAGE_SIZE, "skip": skip}
        if config.OPENFDA_API_KEY:
            params["api_key"] = config.OPENFDA_API_KEY
        response = session.get(URL, params=params, timeout=60)
        if response.status_code == 404:  # openFDA returns 404 when there are no matches
            return results
        response.raise_for_status()
        payload = response.json()
        results.extend(payload.get("results", []))
        total = payload.get("meta", {}).get("results", {}).get("total", 0)
        logger.info("%s: %s / %s recalls", search, len(results), total)
        skip += PAGE_SIZE
        if skip >= total:
            return results


def flatten_recall(record: dict) -> dict:
    row = {field: record.get(field) for field in FIELDS}
    openfda = record.get("openfda", {})
    row["brand_names"] = "|".join(openfda.get("brand_name", [])) or None
    row["generic_names"] = "|".join(openfda.get("generic_name", [])) or None
    return row


def main() -> None:
    with track_run(SOURCE) as run:
        recalls = {}
        for search in SEARCHES:
            for record in fetch_recalls(search):
                recalls[record.get("recall_number")] = record
        logger.info("Unique recalls: %s", len(recalls))

        raw_bytes = json.dumps(list(recalls.values())).encode("utf-8")
        raw_blob = gcs.lake_path("raw", SOURCE, gcs.today_partition(), "recalls.json")
        gcs.upload_bytes(raw_bytes, raw_blob, "application/json")

        df = pd.DataFrame([flatten_recall(r) for r in recalls.values()], columns=FIELDS + ["brand_names", "generic_names"])
        uri, size = upload_dataframe(df, gcs.lake_path("bronze", SOURCE, "recalls.parquet"))

        run["rows_loaded"] = bq.load_parquet(uri, "fda_recalls")
        run["files_written"] = 2
        run["bytes_written"] = len(raw_bytes) + size
        run["target"] = "raw.fda_recalls"


if __name__ == "__main__":
    main()
