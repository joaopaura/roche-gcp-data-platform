"""FDA FAERS / AEMS quarterly ASCII files -> lake (raw zip + bronze Parquet per table and quarter)

Each quarter is a ~60-75 MB zip with 7 '$'-delimited tables (DEMO, DRUG, REAC, OUTC, RPSR, THER, INDI).
Files are read in chunks (low memory), columns are standardised to a fixed schema (all strings),
and written to a Hive-style layout:  bronze/faers/<table>/quarter=2026Q2/<table>.parquet
Quarters already in bronze are skipped (idempotent), unless --force is used.

Run one quarter (measure volumes):  python -m ingestion.batch.faers --start 2026Q2 --end 2026Q2
Run a range:                        python -m ingestion.batch.faers --start 2020Q1 --end 2026Q2
Scheduled (last 2 quarters):        python -m ingestion.batch.faers --recent 2
   quarters not yet published by the FDA are skipped with a warning (the FDA publishes ~1 month after quarter end)
"""
import argparse
import csv
import re
import tempfile
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ingestion.common import gcs
from ingestion.common.http import get_session
from ingestion.common.logger import get_logger
from ingestion.common.run_tracker import track_run

SOURCE = "faers"
URL_TEMPLATES = [
    "https://fis.fda.gov/content/Exports/faers_ascii_{year}q{q}.zip",
    "https://fis.fda.gov/content/Exports/faers_ascii_{year}Q{q}.zip",
]
CHUNK_ROWS = 500_000

# Fixed schema per table (FAERS ASCII specification, 2014+). Missing columns are added as null,
# unexpected ones are logged and dropped, so every quarter has the same schema in BigQuery.
SCHEMAS = {
    "demo": ["primaryid", "caseid", "caseversion", "i_f_code", "event_dt", "mfr_dt", "init_fda_dt",
             "fda_dt", "rept_cod", "auth_num", "mfr_num", "mfr_sndr", "lit_ref", "age", "age_cod",
             "age_grp", "sex", "e_sub", "wt", "wt_cod", "rept_dt", "to_mfr", "occp_cod",
             "reporter_country", "occr_country"],
    "drug": ["primaryid", "caseid", "drug_seq", "role_cod", "drugname", "prod_ai", "val_vbm", "route",
             "dose_vbm", "cum_dose_chr", "cum_dose_unit", "dechal", "rechal", "lot_num", "exp_dt",
             "nda_num", "dose_amt", "dose_unit", "dose_form", "dose_freq"],
    "reac": ["primaryid", "caseid", "pt", "drug_rec_act"],
    "outc": ["primaryid", "caseid", "outc_cod"],
    "rpsr": ["primaryid", "caseid", "rpsr_cod"],
    "ther": ["primaryid", "caseid", "dsg_drug_seq", "start_dt", "end_dt", "dur", "dur_cod"],
    "indi": ["primaryid", "caseid", "indi_drug_seq", "indi_pt"],
}
FILE_PATTERN = re.compile(r"(demo|drug|reac|outc|rpsr|ther|indi)\d{2}q[1-4]\.txt$", re.IGNORECASE)

logger = get_logger(SOURCE)


def quarter_range(start: str, end: str) -> list[str]:
    """quarter_range('2025Q3', '2026Q1') -> ['2025Q3', '2025Q4', '2026Q1']"""
    year, q = int(start[:4]), int(start[-1])
    end_year, end_q = int(end[:4]), int(end[-1])
    quarters = []
    while (year, q) <= (end_year, end_q):
        quarters.append(f"{year}Q{q}")
        year, q = (year + 1, 1) if q == 4 else (year, q + 1)
    return quarters


def recent_quarters(n: int, today: date | None = None) -> list[str]:
    """The n most recent COMPLETED quarters, oldest first. recent_quarters(2, date(2026, 9, 29)) -> ['2026Q1', '2026Q2']"""
    today = today or date.today()
    year, q = today.year, (today.month - 1) // 3 + 1
    quarters = []
    for _ in range(n):
        year, q = (year - 1, 4) if q == 1 else (year, q - 1)
        quarters.append(f"{year}Q{q}")
    return quarters[::-1]


def standardise_columns(df: pd.DataFrame, table: str, unexpected: set) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c and not c.startswith("unnamed")]]
    unexpected.update(set(df.columns) - set(SCHEMAS[table]))
    return df.reindex(columns=SCHEMAS[table])


def download_quarter(quarter: str, folder: Path) -> Path:
    session = get_session()
    year, q = quarter[:4], quarter[-1]
    for template in URL_TEMPLATES:
        url = template.format(year=year, q=q)
        with session.get(url, stream=True, timeout=300) as response:
            if response.status_code == 404:
                continue
            response.raise_for_status()
            path = folder / Path(url).name
            with open(path, "wb") as f:
                for block in response.iter_content(chunk_size=1024 * 1024):
                    f.write(block)
            logger.info("%s downloaded: %.1f MB", quarter, path.stat().st_size / 1e6)
            return path
    raise FileNotFoundError(f"No FAERS file found for {quarter}")


def convert_table(zf: zipfile.ZipFile, member: str, table: str, out_path: Path) -> int:
    schema = pa.schema([(col, pa.string()) for col in SCHEMAS[table]])
    unexpected, rows = set(), 0
    with zf.open(member) as raw, pq.ParquetWriter(out_path, schema, compression="snappy") as writer:
        reader = pd.read_csv(
            raw, sep="$", dtype=str, encoding="latin-1", quoting=csv.QUOTE_NONE,
            keep_default_na=False, na_values=[""], on_bad_lines="warn", chunksize=CHUNK_ROWS,
        )
        for chunk in reader:
            chunk = standardise_columns(chunk, table, unexpected)
            writer.write_table(pa.Table.from_pandas(chunk, schema=schema, preserve_index=False))
            rows += len(chunk)
    if unexpected:
        logger.warning("%s: dropped unexpected columns %s", table, sorted(unexpected))
    return rows


def process_quarter(quarter: str, force: bool, report: list, run: dict) -> None:
    marker = gcs.lake_path("bronze", SOURCE, "demo", f"quarter={quarter}", "demo.parquet")
    if not force and gcs.blob_exists(marker):
        logger.info("%s already in bronze, skipping (use --force to reload)", quarter)
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        zip_path = download_quarter(quarter, tmp)
        gcs.upload_file(zip_path, gcs.lake_path("raw", SOURCE, f"quarter={quarter}", zip_path.name))
        run["files_written"] += 1
        run["bytes_written"] += zip_path.stat().st_size

        with zipfile.ZipFile(zip_path) as zf:
            members = {FILE_PATTERN.search(m).group(1).lower(): m for m in zf.namelist() if FILE_PATTERN.search(m)}
            for table in SCHEMAS:
                if table not in members:
                    logger.warning("%s: table %s not found in zip", quarter, table)
                    continue
                txt_mb = zf.getinfo(members[table]).file_size / 1e6
                out = tmp / f"{table}.parquet"
                rows = convert_table(zf, members[table], table, out)
                parquet_mb = out.stat().st_size / 1e6
                gcs.upload_file(out, gcs.lake_path("bronze", SOURCE, table, f"quarter={quarter}", f"{table}.parquet"))

                run["rows_loaded"] += rows
                run["files_written"] += 1
                run["bytes_written"] += out.stat().st_size
                report.append({"quarter": quarter, "table": table, "rows": rows,
                               "txt_mb": round(txt_mb, 1), "parquet_mb": round(parquet_mb, 1)})
                logger.info("%s %-4s | %10s rows | txt %7.1f MB | parquet %6.1f MB", quarter, table, f"{rows:,}", txt_mb, parquet_mb)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest FAERS quarterly files into the data lake")
    parser.add_argument("--start", help="First quarter, e.g. 2020Q1")
    parser.add_argument("--end", help="Last quarter, e.g. 2026Q2")
    parser.add_argument("--recent", type=int, help="Process the N most recent completed quarters")
    parser.add_argument("--force", action="store_true", help="Reload quarters already in bronze")
    args = parser.parse_args()

    if args.recent:
        quarters = recent_quarters(args.recent)
    elif args.start and args.end:
        quarters = quarter_range(args.start.upper(), args.end.upper())
    else:
        parser.error("use --recent N or --start and --end")

    report = []
    with track_run(SOURCE) as run:
        for quarter in quarters:
            try:
                process_quarter(quarter, args.force, report, run)
            except FileNotFoundError:
                if not args.recent:
                    raise
                logger.warning("%s not published by the FDA yet, skipping", quarter)
        run["target"] = f"bronze/faers ({quarters[0]}-{quarters[-1]})"

    if report:
        summary = pd.DataFrame(report).groupby("table")[["rows", "txt_mb", "parquet_mb"]].sum()
        print("\n=== Volume summary ===")
        print(summary.to_string())
        print(f"TOTAL: {summary['rows'].sum():,} rows | txt {summary['txt_mb'].sum():.0f} MB | parquet {summary['parquet_mb'].sum():.0f} MB")


if __name__ == "__main__":
    main()
