"""ClinicalTrials.gov API v2: studies sponsored by Roche / Genentech -> lake -> raw.ct_studies

Full daily snapshot (a few thousand studies). History of status changes is kept later
with a dbt snapshot (SCD type 2).

Run:  python -m ingestion.batch.clinical_trials
"""
import gzip
import json

import pandas as pd

from ingestion.common import bq, gcs
from ingestion.common.http import get_session
from ingestion.common.logger import get_logger
from ingestion.common.parquet import upload_dataframe
from ingestion.common.run_tracker import track_run

SOURCE = "clinical_trials"
URL = "https://clinicaltrials.gov/api/v2/studies"
SPONSORS = ["Hoffmann-La Roche", "Genentech, Inc."]
PAGE_SIZE = 1000

logger = get_logger(SOURCE)


def fetch_studies(sponsor: str) -> list[dict]:
    session = get_session()
    params = {"query.spons": sponsor, "pageSize": PAGE_SIZE, "format": "json", "countTotal": "true"}
    studies = []
    while True:
        response = session.get(URL, params=params, timeout=120)
        response.raise_for_status()
        payload = response.json()
        studies.extend(payload.get("studies", []))
        logger.info("%s: %s / %s studies", sponsor, len(studies), payload.get("totalCount", "?"))
        token = payload.get("nextPageToken")
        if not token:
            return studies
        params["pageToken"] = token


def _date(module: dict, key: str):
    return (module.get(key) or {}).get("date")


def _join(values) -> str | None:
    values = [v for v in values if v]
    return "|".join(dict.fromkeys(values)) if values else None


def flatten_study(study: dict) -> dict:
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    status = ps.get("statusModule", {})
    sponsor = ps.get("sponsorCollaboratorsModule", {})
    design = ps.get("designModule", {})
    conditions = ps.get("conditionsModule", {})
    arms = ps.get("armsInterventionsModule", {})
    locations = ps.get("contactsLocationsModule", {}).get("locations", [])
    meshes = study.get("derivedSection", {}).get("conditionBrowseModule", {}).get("meshes", [])
    enrollment = design.get("enrollmentInfo", {})

    return {
        "nct_id": ident.get("nctId"),
        "brief_title": ident.get("briefTitle"),
        "acronym": ident.get("acronym"),
        "overall_status": status.get("overallStatus"),
        "why_stopped": status.get("whyStopped"),
        "start_date": _date(status, "startDateStruct"),
        "primary_completion_date": _date(status, "primaryCompletionDateStruct"),
        "completion_date": _date(status, "completionDateStruct"),
        "first_post_date": _date(status, "studyFirstPostDateStruct"),
        "last_update_post_date": _date(status, "lastUpdatePostDateStruct"),
        "lead_sponsor": sponsor.get("leadSponsor", {}).get("name"),
        "lead_sponsor_class": sponsor.get("leadSponsor", {}).get("class"),
        "collaborators": _join(c.get("name") for c in sponsor.get("collaborators", [])),
        "study_type": design.get("studyType"),
        "phases": _join(design.get("phases", [])),
        "enrollment_count": enrollment.get("count"),
        "enrollment_type": enrollment.get("type"),
        "conditions": _join(conditions.get("conditions", [])),
        "keywords": _join(conditions.get("keywords", [])),
        "mesh_terms": _join(m.get("term") for m in meshes),
        "intervention_types": _join(i.get("type") for i in arms.get("interventions", [])),
        "interventions": _join(i.get("name") for i in arms.get("interventions", [])),
        "countries": _join(loc.get("country") for loc in locations),
        "location_count": len(locations),
        "has_results": study.get("hasResults"),
    }


def main() -> None:
    with track_run(SOURCE) as run:
        all_studies = {}
        for sponsor in SPONSORS:
            for study in fetch_studies(sponsor):
                nct_id = study.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
                all_studies[nct_id] = study  # dedup: a study can match both sponsors
        logger.info("Unique studies: %s", len(all_studies))

        raw_lines = "\n".join(json.dumps(s) for s in all_studies.values()).encode("utf-8")
        raw_bytes = gzip.compress(raw_lines)
        raw_blob = gcs.lake_path("raw", SOURCE, gcs.today_partition(), "studies.jsonl.gz")
        gcs.upload_bytes(raw_bytes, raw_blob, "application/gzip")

        df = pd.DataFrame([flatten_study(s) for s in all_studies.values()])
        df["enrollment_count"] = pd.to_numeric(df["enrollment_count"], errors="coerce").astype("Int64")
        df["snapshot_date"] = pd.Timestamp.today().date()

        bronze_blob = gcs.lake_path("bronze", SOURCE, "studies.parquet")
        uri, size = upload_dataframe(df, bronze_blob)

        run["rows_loaded"] = bq.load_parquet(uri, "ct_studies")
        run["files_written"] = 2
        run["bytes_written"] = len(raw_bytes) + size
        run["target"] = "raw.ct_studies"


if __name__ == "__main__":
    main()
