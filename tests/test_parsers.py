"""Unit tests for the pure transformation functions (no network, no GCP)."""
import pandas as pd

from ingestion.batch.clinical_trials import flatten_study
from ingestion.batch.ecb_fx import parse_ecb_csv
from ingestion.batch.faers import quarter_range, standardise_columns
from ingestion.batch.openfda_enforcement import flatten_recall


def test_quarter_range_crosses_year():
    assert quarter_range("2025Q3", "2026Q1") == ["2025Q3", "2025Q4", "2026Q1"]


def test_quarter_range_single():
    assert quarter_range("2026Q2", "2026Q2") == ["2026Q2"]


def test_standardise_columns_adds_missing_and_drops_extra():
    df = pd.DataFrame({"PRIMARYID": ["1"], "CaseID": ["10"], "pt": ["Nausea"], "Unnamed: 4": [None], "new_col": ["x"]})
    unexpected = set()
    out = standardise_columns(df, "reac", unexpected)
    assert list(out.columns) == ["primaryid", "caseid", "pt", "drug_rec_act"]
    assert out["drug_rec_act"].isna().all()
    assert unexpected == {"new_col"}


def test_parse_ecb_csv():
    text = (
        "KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE\n"
        "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-09-01,1.10\n"
        "EXR.D.CHF.EUR.SP00.A,D,CHF,EUR,SP00,A,2026-09-01,0.94\n"
        "EXR.D.CHF.EUR.SP00.A,D,CHF,EUR,SP00,A,2026-09-02,\n"
    )
    df = parse_ecb_csv(text)
    assert len(df) == 2
    assert set(df["currency"]) == {"USD", "CHF"}
    assert list(df.columns) == ["rate_date", "currency", "base_currency", "rate"]


def test_flatten_study():
    study = {
        "hasResults": True,
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001", "briefTitle": "A study"},
            "statusModule": {"overallStatus": "RECRUITING", "startDateStruct": {"date": "2024-05"}},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Hoffmann-La Roche", "class": "INDUSTRY"}},
            "designModule": {"phases": ["PHASE2", "PHASE3"], "enrollmentInfo": {"count": 300}},
            "contactsLocationsModule": {"locations": [{"country": "Spain"}, {"country": "Spain"}, {"country": "Poland"}]},
        },
    }
    row = flatten_study(study)
    assert row["nct_id"] == "NCT00000001"
    assert row["phases"] == "PHASE2|PHASE3"
    assert row["countries"] == "Spain|Poland"
    assert row["location_count"] == 3
    assert row["start_date"] == "2024-05"


def test_flatten_recall():
    row = flatten_recall({"recall_number": "D-1-2024", "openfda": {"brand_name": ["OCREVUS"]}})
    assert row["recall_number"] == "D-1-2024"
    assert row["brand_names"] == "OCREVUS"
    assert row["generic_names"] is None


def test_convert_table_from_zip(tmp_path):
    """FAERS text ('$' delimited, trailing '$', latin-1) -> Parquet with the fixed schema."""
    import zipfile

    import pyarrow.parquet as pq

    from ingestion.batch.faers import convert_table

    content = "primaryid$caseid$pt$drug_rec_act$\n100$10$Náusea$$\n200$20$Headache$Yes$\n"
    zip_path = tmp_path / "faers.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("ASCII/REAC26Q2.txt", content.encode("latin-1"))

    out = tmp_path / "reac.parquet"
    with zipfile.ZipFile(zip_path) as zf:
        rows = convert_table(zf, "ASCII/REAC26Q2.txt", "reac", out)

    table = pq.read_table(out).to_pandas()
    assert rows == 2
    assert list(table.columns) == ["primaryid", "caseid", "pt", "drug_rec_act"]
    assert table.loc[0, "pt"] == "Náusea"
    assert table.loc[1, "drug_rec_act"] == "Yes"
