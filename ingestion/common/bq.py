"""BigQuery helpers: load Parquet from the lake (load jobs are free) and write the run log."""
from google.cloud import bigquery

from ingestion.common import config
from ingestion.common.auth import get_credentials

_client = None

RUN_LOG_SCHEMA = [
    bigquery.SchemaField("run_id", "STRING"),
    bigquery.SchemaField("source", "STRING"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("started_at", "TIMESTAMP"),
    bigquery.SchemaField("finished_at", "TIMESTAMP"),
    bigquery.SchemaField("duration_sec", "FLOAT"),
    bigquery.SchemaField("rows_loaded", "INTEGER"),
    bigquery.SchemaField("files_written", "INTEGER"),
    bigquery.SchemaField("bytes_written", "INTEGER"),
    bigquery.SchemaField("target", "STRING"),
    bigquery.SchemaField("triggered_by", "STRING"),
    bigquery.SchemaField("error_message", "STRING"),
]


def get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(
            project=config.PROJECT_ID, credentials=get_credentials(), location=config.REGION
        )
    return _client


def table_id(dataset: str, table: str) -> str:
    return f"{config.PROJECT_ID}.{dataset}.{table}"


def load_parquet(uris, table: str, dataset: str = config.RAW_DATASET,
                 write_disposition: str = "WRITE_TRUNCATE", hive_prefix: str | None = None) -> int:
    """Load one or more Parquet files from GCS into BigQuery. Returns the table row count."""
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=write_disposition,
    )
    if hive_prefix:
        hive = bigquery.HivePartitioningOptions()
        hive.mode = "STRINGS"
        hive.source_uri_prefix = hive_prefix
        job_config.hive_partitioning = hive

    client = get_client()
    job = client.load_table_from_uri(uris, table_id(dataset, table), job_config=job_config)
    job.result()
    return client.get_table(table_id(dataset, table)).num_rows


def log_run(run: dict) -> None:
    """Append one row to ops.ingestion_runs (load job, not streaming insert, so it is free)."""
    job_config = bigquery.LoadJobConfig(
        schema=RUN_LOG_SCHEMA,
        write_disposition="WRITE_APPEND",
        create_disposition="CREATE_IF_NEEDED",
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    row = {field.name: run.get(field.name) for field in RUN_LOG_SCHEMA}
    get_client().load_table_from_json(
        [row], table_id(config.OPS_DATASET, "ingestion_runs"), job_config=job_config
    ).result()


def load_json_from_gcs(uri: str, table: str, schema: list, dataset: str = config.RAW_DATASET,
                       partition_field: str | None = None) -> None:
    """Append a newline-delimited JSON file (can be .gz) from GCS into BigQuery with an explicit schema."""
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=schema,
        write_disposition="WRITE_APPEND",
        create_disposition="CREATE_IF_NEEDED",
        ignore_unknown_values=True,
    )
    if partition_field:
        job_config.time_partitioning = bigquery.TimePartitioning(field=partition_field)
    get_client().load_table_from_uri(uri, table_id(dataset, table), job_config=job_config).result()


def append_rows(rows: list[dict], table: str, schema: list, dataset: str = config.OPS_DATASET) -> None:
    """Append small in-memory rows with a load job (free, unlike streaming inserts)."""
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_APPEND",
        create_disposition="CREATE_IF_NEEDED",
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    get_client().load_table_from_json(rows, table_id(dataset, table), job_config=job_config).result()
