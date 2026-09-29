"""Profile the raw layer (schemas + key value distributions) into data/tmp/raw_profile.md.
Used to design the dbt models from real column names and values.

Run:  python -m tools.profile_raw
"""
from pathlib import Path

from ingestion.common import bq, config

P = config.PROJECT_ID
ROCHE = r"ROCHE|GENENTECH|HOFFMANN|CHUGAI"

QUERIES = {
    "Columns raw": f"""SELECT table_name, STRING_AGG(column_name || ':' || data_type, ', ' ORDER BY ordinal_position)
        FROM `{P}.raw.INFORMATION_SCHEMA.COLUMNS` GROUP BY 1 ORDER BY 1""",
    "Columns ops": f"""SELECT table_name, STRING_AGG(column_name || ':' || data_type, ', ' ORDER BY ordinal_position)
        FROM `{P}.ops.INFORMATION_SCHEMA.COLUMNS` GROUP BY 1 ORDER BY 1""",
    "CMS Part D rows mentioning Roche/Genentech": f"""SELECT TO_JSON_STRING(t) FROM `{P}.raw.cms_part_d` t
        WHERE REGEXP_CONTAINS(UPPER(TO_JSON_STRING(t)), r'{ROCHE}') LIMIT 60""",
    "CMS Part B rows mentioning Roche/Genentech": f"""SELECT TO_JSON_STRING(t) FROM `{P}.raw.cms_part_b` t
        WHERE REGEXP_CONTAINS(UPPER(TO_JSON_STRING(t)), r'{ROCHE}') LIMIT 60""",
    "CMS Part B sample (first 3 rows)": f"SELECT TO_JSON_STRING(t) FROM `{P}.raw.cms_part_b` t LIMIT 3",
    "FAERS demo volume": f"""SELECT COUNT(*) AS rows_, COUNT(DISTINCT primaryid) AS primaryids, COUNT(DISTINCT caseid) AS caseids
        FROM `{P}.raw.faers_demo`""",
    "FAERS mfr_sndr Roche group": f"""SELECT UPPER(mfr_sndr) AS sender, COUNT(*) AS n FROM `{P}.raw.faers_demo`
        WHERE REGEXP_CONTAINS(UPPER(mfr_sndr), r'{ROCHE}') GROUP BY 1 ORDER BY n DESC LIMIT 30""",
    "FAERS top PS prod_ai in Roche-sent cases": f"""SELECT UPPER(d.prod_ai) AS prod_ai, COUNT(DISTINCT d.primaryid) AS cases,
          ANY_VALUE(UPPER(d.drugname)) AS example_drugname
        FROM `{P}.raw.faers_drug` d
        JOIN (SELECT primaryid FROM `{P}.raw.faers_demo` WHERE REGEXP_CONTAINS(UPPER(mfr_sndr), r'{ROCHE}')) r USING (primaryid)
        WHERE d.role_cod = 'PS' GROUP BY 1 ORDER BY cases DESC LIMIT 80""",
    "FAERS top PS drugname in Roche-sent cases": f"""SELECT UPPER(d.drugname) AS drugname, COUNT(DISTINCT d.primaryid) AS cases
        FROM `{P}.raw.faers_drug` d
        JOIN (SELECT primaryid FROM `{P}.raw.faers_demo` WHERE REGEXP_CONTAINS(UPPER(mfr_sndr), r'{ROCHE}')) r USING (primaryid)
        WHERE d.role_cod = 'PS' GROUP BY 1 ORDER BY cases DESC LIMIT 80""",
    "FAERS PS prod_ai for key molecules (all senders)": f"""SELECT UPPER(prod_ai) AS prod_ai, COUNT(DISTINCT primaryid) AS cases
        FROM `{P}.raw.faers_drug` WHERE role_cod = 'PS'
          AND REGEXP_CONTAINS(UPPER(prod_ai), r'TRASTUZUMAB|BEVACIZUMAB|RITUXIMAB|TOCILIZUMAB|RANIBIZUMAB|OCRELIZUMAB|EMICIZUMAB|FARICIMAB|ATEZOLIZUMAB|OMALIZUMAB|PERTUZUMAB')
        GROUP BY 1 ORDER BY cases DESC LIMIT 60""",
    "FAERS code distributions": f"""SELECT 'outc' AS t, outc_cod AS code, COUNT(*) AS n FROM `{P}.raw.faers_outc` GROUP BY 2
        UNION ALL SELECT 'role', role_cod, COUNT(*) FROM `{P}.raw.faers_drug` WHERE quarter = '2026Q2' GROUP BY 2
        UNION ALL SELECT 'occp', occp_cod, COUNT(*) FROM `{P}.raw.faers_demo` WHERE quarter = '2026Q2' GROUP BY 2
        UNION ALL SELECT 'rept', rept_cod, COUNT(*) FROM `{P}.raw.faers_demo` WHERE quarter = '2026Q2' GROUP BY 2
        ORDER BY 1, 3 DESC""",
    "FAERS date formats sample": f"""SELECT fda_dt, event_dt, init_fda_dt, age, age_cod, wt, wt_cod, sex, caseversion
        FROM `{P}.raw.faers_demo` WHERE quarter = '2026Q2' LIMIT 15""",
    "ClinicalTrials status / phase / type / sponsor": f"""SELECT 'status' AS k, overall_status AS v, COUNT(*) AS n FROM `{P}.raw.ct_studies` GROUP BY 2
        UNION ALL SELECT 'phases', phases, COUNT(*) FROM `{P}.raw.ct_studies` GROUP BY 2
        UNION ALL SELECT 'type', study_type, COUNT(*) FROM `{P}.raw.ct_studies` GROUP BY 2
        UNION ALL SELECT 'lead', lead_sponsor, COUNT(*) FROM `{P}.raw.ct_studies` GROUP BY 2
        ORDER BY 1, 3 DESC""",
    "ClinicalTrials date formats + top mesh": f"""SELECT start_date, primary_completion_date, completion_date, last_update_post_date,
          SUBSTR(mesh_terms, 1, 120) AS mesh, SUBSTR(interventions, 1, 120) AS interventions
        FROM `{P}.raw.ct_studies` WHERE overall_status = 'RECRUITING' LIMIT 15""",
    "Recalls": f"""SELECT recall_number, classification, status, recall_initiation_date, brand_names,
          SUBSTR(reason_for_recall, 1, 100) FROM `{P}.raw.fda_recalls`""",
    "ECB range": f"""SELECT currency, MIN(rate_date), MAX(rate_date), COUNT(*), ROUND(AVG(rate), 4)
        FROM `{P}.raw.ecb_fx_rates` GROUP BY 1""",
    "Ingestion runs": f"""SELECT source, status, rows_loaded, ROUND(duration_sec) AS sec, started_at
        FROM `{P}.ops.ingestion_runs` ORDER BY started_at""",
}


def main() -> None:
    client = bq.get_client()
    lines = ["# Raw layer profile\n"]
    for title, sql in QUERIES.items():
        print(f"Running: {title}")
        lines.append(f"\n## {title}\n")
        try:
            job = client.query(sql)
            rows = list(job.result())
            lines.append(f"_{len(rows)} rows | {job.total_bytes_processed / 1e6:.1f} MB processed_\n")
            for row in rows:
                lines.append(" | ".join("" if v is None else str(v) for v in row.values()))
        except Exception as exc:
            lines.append(f"ERROR: {exc}")
    out = config.REPO_ROOT / "data" / "tmp" / "raw_profile.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Profile written to {out}")


if __name__ == "__main__":
    main()
