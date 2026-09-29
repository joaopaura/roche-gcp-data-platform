"""Event contract for the adverse event intake stream: build, validate and fault injection.

One event = one FAERS case (report version) as a nested document, similar to an ICH E2B
safety report: case header + patient + drugs[] + reactions[] + outcomes[].
"""
import random
import uuid
from datetime import datetime, timezone

import pandas as pd
from google.cloud import bigquery

SCHEMA_VERSION = 1
REQUIRED_FIELDS = ["event_id", "primaryid", "caseid", "fda_dt", "received_at"]
CASE_FIELDS = ["primaryid", "caseid", "caseversion", "fda_dt", "event_dt", "rept_cod", "occp_cod",
               "reporter_country", "occr_country", "mfr_sndr"]
PATIENT_FIELDS = ["age", "age_cod", "sex", "wt", "wt_cod"]
DRUG_FIELDS = ["drug_seq", "role_cod", "drugname", "prod_ai", "route"]

# BigQuery schema of raw.faers_stream_events (nested and repeated fields)
BQ_SCHEMA = [
    bigquery.SchemaField("event_id", "STRING"),
    bigquery.SchemaField("event_type", "STRING"),
    bigquery.SchemaField("schema_version", "INTEGER"),
    bigquery.SchemaField("source_quarter", "STRING"),
    bigquery.SchemaField("received_at", "TIMESTAMP"),
    *[bigquery.SchemaField(f, "STRING") for f in CASE_FIELDS],
    bigquery.SchemaField("patient", "RECORD", fields=[bigquery.SchemaField(f, "STRING") for f in PATIENT_FIELDS]),
    bigquery.SchemaField("drugs", "RECORD", mode="REPEATED",
                         fields=[bigquery.SchemaField(f, "STRING") for f in DRUG_FIELDS]),
    bigquery.SchemaField("reactions", "STRING", mode="REPEATED"),
    bigquery.SchemaField("outcomes", "STRING", mode="REPEATED"),
    bigquery.SchemaField("kafka_partition", "INTEGER"),
    bigquery.SchemaField("kafka_offset", "INTEGER"),
    bigquery.SchemaField("batch_id", "STRING"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP"),
]


def _clean(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def build_event(case: dict, drugs: list[dict], reactions: list, outcomes: list, quarter: str) -> dict:
    return {
        "event_id": uuid.uuid4().hex,
        "event_type": "adverse_event_report",
        "schema_version": SCHEMA_VERSION,
        "source_quarter": quarter,
        "received_at": datetime.now(timezone.utc).isoformat(),
        **{f: _clean(case.get(f)) for f in CASE_FIELDS},
        "patient": {f: _clean(case.get(f)) for f in PATIENT_FIELDS},
        "drugs": [{f: _clean(d.get(f)) for f in DRUG_FIELDS} for d in drugs],
        "reactions": [str(r) for r in reactions if _clean(r)],
        "outcomes": [str(o) for o in outcomes if _clean(o)],
    }


def _is_yyyymmdd(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y%m%d")
        return True
    except (TypeError, ValueError):
        return False


def validate_event(event: dict) -> list[str]:
    """Return a list of validation errors (empty list = valid event)."""
    errors = [f"missing {field}" for field in REQUIRED_FIELDS if not event.get(field)]
    if event.get("fda_dt") and not _is_yyyymmdd(event["fda_dt"]):
        errors.append("invalid fda_dt")
    drugs = event.get("drugs") or []
    if not drugs:
        errors.append("no drugs")
    elif not any(d.get("role_cod") == "PS" for d in drugs):
        errors.append("no primary suspect drug")
    if not event.get("reactions"):
        errors.append("no reactions")
    return errors


def inject_fault(event: dict, rng: random.Random) -> dict:
    """Break an event on purpose (demo of validation + dead-letter queue)."""
    fault = rng.choice(["missing_primaryid", "no_reactions", "bad_date", "no_suspect_drug"])
    if fault == "missing_primaryid":
        event["primaryid"] = None
    elif fault == "no_reactions":
        event["reactions"] = []
    elif fault == "bad_date":
        event["fda_dt"] = "20261345"
    else:
        event["drugs"] = [{**d, "role_cod": "C"} for d in event["drugs"]]
    return event
