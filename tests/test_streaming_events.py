"""Unit tests for the streaming event contract (no Kafka, no GCP)."""
import random

from ingestion.streaming.events import build_event, inject_fault, validate_event

CASE = {"primaryid": "123", "caseid": "12", "caseversion": "1", "fda_dt": "20260415",
        "mfr_sndr": "ROCHE", "age": "54", "sex": "F", "wt": None}
DRUGS = [{"drug_seq": "1", "role_cod": "PS", "drugname": "OCREVUS", "prod_ai": "OCRELIZUMAB", "route": "Intravenous"}]


def make_event():
    return build_event(CASE, DRUGS, ["Infusion related reaction"], ["HO"], "2026Q2")


def test_build_event_structure():
    event = make_event()
    assert event["primaryid"] == "123"
    assert event["patient"] == {"age": "54", "age_cod": None, "sex": "F", "wt": None, "wt_cod": None}
    assert event["drugs"][0]["prod_ai"] == "OCRELIZUMAB"
    assert event["reactions"] == ["Infusion related reaction"]
    assert len(event["event_id"]) == 32


def test_valid_event_has_no_errors():
    assert validate_event(make_event()) == []


def test_validation_catches_each_problem():
    event = make_event()
    event.update(primaryid=None, fda_dt="20261345", reactions=[], drugs=[{**DRUGS[0], "role_cod": "C"}])
    errors = validate_event(event)
    assert "missing primaryid" in errors
    assert "invalid fda_dt" in errors
    assert "no reactions" in errors
    assert "no primary suspect drug" in errors


def test_injected_faults_are_always_invalid():
    rng = random.Random(1)
    for _ in range(50):
        assert validate_event(inject_fault(make_event(), rng)) != []
