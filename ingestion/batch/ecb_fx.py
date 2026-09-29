"""ECB daily reference rates (USD and CHF per EUR) -> lake -> raw.ecb_fx_rates

Roche reports in CHF, US spend data is in USD: USD->CHF is derived later in dbt
(CHF per EUR / USD per EUR).

Run:  python -m ingestion.batch.ecb_fx
"""
import io

import pandas as pd

from ingestion.common import bq, gcs
from ingestion.common.http import get_session
from ingestion.common.logger import get_logger
from ingestion.common.parquet import upload_dataframe
from ingestion.common.run_tracker import track_run

SOURCE = "ecb_fx"
URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD+CHF.EUR.SP00.A"
START_PERIOD = "2019-01-01"

logger = get_logger(SOURCE)


def parse_ecb_csv(text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text))
    df = df[["TIME_PERIOD", "CURRENCY", "CURRENCY_DENOM", "OBS_VALUE"]].rename(
        columns={
            "TIME_PERIOD": "rate_date",
            "CURRENCY": "currency",
            "CURRENCY_DENOM": "base_currency",
            "OBS_VALUE": "rate",
        }
    )
    df["rate_date"] = pd.to_datetime(df["rate_date"]).dt.date
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    return df.dropna(subset=["rate"]).sort_values(["currency", "rate_date"]).reset_index(drop=True)


def main() -> None:
    with track_run(SOURCE) as run:
        response = get_session().get(
            URL, params={"format": "csvdata", "startPeriod": START_PERIOD}, timeout=60
        )
        response.raise_for_status()

        raw_blob = gcs.lake_path("raw", SOURCE, gcs.today_partition(), "exr_usd_chf_eur.csv")
        gcs.upload_bytes(response.content, raw_blob, "text/csv")

        df = parse_ecb_csv(response.text)
        logger.info("Parsed %s rates from %s to %s", len(df), df["rate_date"].min(), df["rate_date"].max())

        bronze_blob = gcs.lake_path("bronze", SOURCE, "fx_rates.parquet")
        uri, size = upload_dataframe(df, bronze_blob)

        run["rows_loaded"] = bq.load_parquet(uri, "ecb_fx_rates")
        run["files_written"] = 2
        run["bytes_written"] = len(response.content) + size
        run["target"] = "raw.ecb_fx_rates"


if __name__ == "__main__":
    main()
