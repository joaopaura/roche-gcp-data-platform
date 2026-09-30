"""Render the Power BI page backgrounds (1920x1080 PNG) from HTML.
Everything static is baked in: page title, navigation button labels, KPI card labels,
chart titles/subtitles, architecture diagram and footer. Visuals in Power BI have titles OFF."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("/home/claude/pbi/backgrounds"); OUT.mkdir(parents=True, exist_ok=True)
import base64
LOGO = "data:image/png;base64," + base64.b64encode(Path(__file__).with_name("roche_logo.png").read_bytes()).decode()

T = dict(bg="#F4F6FA", panel="#FFFFFF", border="#E2E7EF", ink="#0A1F44", ink2="#5B6576",
         muted="#8A93A3", blue="#0B41CD", blue_soft="#E8EEFC")

KPI_X = [48, 357, 667, 976, 1285, 1595]; KPI_W = 277; KPI_Y = 180; KPI_H = 116
ROW2_Y, ROW2_H = 316, 350
ROW3_Y, ROW3_H = 686, 334
TWO = [(48, 900), (972, 900)]
THREE = [(48, 592), (664, 592), (1280, 592)]
NAV = ["Home", "Commercial", "R&D Pipeline", "Safety", "Pipeline Health"]
NAV_X0, NAV_Y, NAV_W, NAV_H, NAV_GAP = 988, 30, 128, 40, 8
SLICER_X = [48, 290, 532, 774]; SLICER_Y = 124; SLICER_W = 226

FOOTER = ("Developed by <b>João Paúra</b> | Data Engineering &amp; BI portfolio project | "
          "Public data: FDA FAERS/AEMS, openFDA, CMS Medicare Part B &amp; D, ClinicalTrials.gov, ECB | "
          "Independent project, not affiliated with or endorsed by Roche")
FOOTER_R = "linkedin.com/in/joaopaura | github.com/joaopaura"

CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1920px;height:1080px;background:{T['bg']};font-family:'Inter',sans-serif;color:{T['ink']};position:relative;overflow:hidden}}
.abs{{position:absolute}}
.title{{left:48px;top:24px;font-size:30px;font-weight:650;letter-spacing:-0.3px}}
.title span{{color:{T['blue']}}}
.sub{{left:48px;top:68px;font-size:15px;color:{T['ink2']};width:920px;line-height:1.35;white-space:nowrap}}
.nav{{height:{NAV_H}px;width:{NAV_W}px;border-radius:8px;border:1px solid {T['border']};background:#fff;
      font-size:14px;font-weight:550;display:flex;align-items:center;justify-content:center;color:{T['ink']}}}
.nav.on{{background:{T['blue']};border-color:{T['blue']};color:#fff}}
.logo{{left:1712px;top:22px;width:160px;height:56px}}
.slabel{{font-size:12px;font-weight:600;color:{T['ink2']};text-transform:uppercase;letter-spacing:.6px}}
.card{{background:{T['panel']};border:1px solid {T['border']};border-radius:12px;box-shadow:0 1px 2px rgba(10,31,68,.04)}}
.kpi .l{{position:absolute;left:20px;top:16px;font-size:13px;font-weight:600;color:{T['ink2']}}}
.kpi .bar{{position:absolute;left:0;top:18px;width:4px;height:16px;border-radius:0 3px 3px 0;background:{T['blue']}}}
.panel .h{{position:absolute;left:24px;top:18px;font-size:17px;font-weight:650}}
.panel .s{{position:absolute;left:24px;top:44px;font-size:12.5px;color:{T['ink2']}}}
.footer{{left:48px;top:1044px;font-size:12px;color:{T['muted']}}}
.footer b{{color:{T['ink2']};font-weight:650}}
.footr{{right:48px;top:1044px;font-size:12px;color:{T['ink2']};font-weight:550}}
.fline{{left:48px;top:1032px;width:1824px;height:1px;background:{T['border']}}}
"""

def base(inner: str) -> str:
    return (f"<html><head><style>{CSS}</style></head><body>{inner}"
            f"<div class='abs fline'></div><div class='abs footer'>{FOOTER}</div>"
            f"<div class='abs footr'>{FOOTER_R}</div></body></html>")

def nav(active: int) -> str:
    html = ""
    for i, name in enumerate(NAV):
        x = NAV_X0 + i * (NAV_W + NAV_GAP)
        html += f"<div class='abs nav{' on' if i == active else ''}' style='left:{x}px;top:{NAV_Y}px'>{name}</div>"
    return html + f"<img class='abs' src='{LOGO}' style='right:48px;top:22px;height:56px'>"

def page(p: dict) -> str:
    h = f"<div class='abs title'>{p['title']}</div><div class='abs sub'>{p['sub']}</div>" + nav(p["nav"])
    for x, label in zip(SLICER_X, p["slicers"]):
        h += f"<div class='abs slabel' style='left:{x}px;top:{SLICER_Y - 18}px'>{label}</div>"
    h += f"<div class='abs slabel' style='left:1622px;top:{SLICER_Y - 18}px'>Data as of</div>"
    for x, label in zip(KPI_X, p["kpis"]):
        h += (f"<div class='abs card kpi' style='left:{x}px;top:{KPI_Y}px;width:{KPI_W}px;height:{KPI_H}px'>"
              f"<div class='bar'></div><div class='l'>{label}</div></div>")
    for (x, y, w, hh, title, sub, extra) in p["panels"]:
        h += (f"<div class='abs card panel' style='left:{x}px;top:{y}px;width:{w}px;height:{hh}px'>"
              f"<div class='h'>{title}</div><div class='s'>{sub}</div>{extra}</div>")
    return base(h)

def arch() -> str:
    box = ("display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;"
           "border-radius:10px;font-size:13px;font-weight:600;padding:8px;line-height:1.3")
    def b(x, y, w, hh, t, s, fill, color="#0A1F44"):
        return (f"<div class='abs' style='left:{x}px;top:{y}px;width:{w}px;height:{hh}px;{box};background:{fill};color:{color}'>"
                f"{t}<span style='font-size:11px;font-weight:450;opacity:.8;margin-top:3px'>{s}</span></div>")
    def arrow(x, y, w):
        return (f"<div class='abs' style='left:{x}px;top:{y}px;width:{w}px;height:2px;background:#9AA7BD'></div>"
                f"<div class='abs' style='left:{x + w - 7}px;top:{y - 4}px;width:0;height:0;border-left:8px solid #9AA7BD;"
                f"border-top:5px solid transparent;border-bottom:5px solid transparent'></div>")
    s = ""
    W, G = 170, 40
    X = [24 + i * (W + G) for i in range(6)]
    s += b(X[0], 84, W, 172, "Public sources", "FDA FAERS / AEMS<br>openFDA recalls<br>CMS Medicare B &amp; D<br>ClinicalTrials.gov<br>ECB FX rates", "#EEF1F6")
    s += b(X[1], 84, W, 76, "Python batch", "GitHub Actions<br>daily / monthly", "#E8EEFC")
    s += b(X[1], 180, W, 76, "Kafka streaming", "Producer, consumer, DLQ", "#FDEBDD")
    s += b(X[2], 84, W, 172, "Data lake", "Cloud Storage<br>raw + bronze Parquet<br>~1.9 GB, 157M rows", "#E8EEFC")
    s += b(X[3], 84, W, 172, "Warehouse", "BigQuery<br>external tables +<br>load jobs", "#E8EEFC")
    s += b(X[4], 84, W, 172, "Transform", "dbt Core<br>staging, intermediate,<br>marts, 90+ tests", "#E3F4EF")
    s += b(X[5], 84, 110, 172, "Power BI", "Import mode<br>5 pages", "#0B41CD", "#FFFFFF")
    for i in range(5):
        if i == 0:
            s += arrow(X[0] + W, 122, G) + arrow(X[0] + W, 218, G)
        elif i == 1:
            s += arrow(X[1] + W, 122, G) + arrow(X[1] + W, 218, G)
        else:
            s += arrow(X[i] + W, 170, G)
    s += b(24, 272, 1160, 44, "Terraform (IaC) | Workload Identity Federation (keyless) | GitHub Actions CI/CD | Ops monitoring tables", "", "#F4F6FA")
    return s

PAGES = {
    "02_commercial": dict(
        nav=1, title="Commercial <span>|</span> US Medicare spend",
        sub="Real Medicare Part B and D spend on Roche / Genentech products, 2020 to 2024 | USD and CHF (ECB annual average)",
        slicers=["Year", "Program", "Therapeutic area", "Portfolio segment"],
        kpis=["Total Medicare spend", "Spend in CHF", "Growth vs prior year", "Growth brands share", "Loss of exclusivity erosion", "Medicare claims"],
        panels=[(TWO[0][0], ROW2_Y, TWO[0][1], ROW2_H, "Spend by portfolio segment", "Growth brands, established brands and loss of exclusivity, USD m per year", ""),
                (TWO[1][0], ROW2_Y, TWO[1][1], ROW2_H, "Biosimilar erosion vs growth brands", "Spend indexed to 2020 = 100", ""),
                (TWO[0][0], ROW3_Y, TWO[0][1], ROW3_H, "Top 10 products by spend", "Selected year, USD m and change vs prior year", ""),
                (TWO[1][0], ROW3_Y, TWO[1][1], ROW3_H, "Spend by therapeutic area", "Share of selected year spend", "")]),
    "03_rd_pipeline": dict(
        nav=2, title="R&amp;D Pipeline <span>|</span> Clinical trials",
        sub="ClinicalTrials.gov studies sponsored or co-sponsored by Roche and Genentech | Daily snapshot, status history (SCD2)",
        slicers=["Therapeutic area", "Phase", "Status", "Roche product"],
        kpis=["Roche-led trials", "Active trials", "Active Phase 3", "Readouts next 12 months", "Patients in active trials", "Stopped early rate"],
        panels=[(TWO[0][0], ROW2_Y, TWO[0][1], ROW2_H, "Pipeline by phase", "Active Roche-led trials per development phase", ""),
                (TWO[1][0], ROW2_Y, TWO[1][1], ROW2_H, "Active trials by therapeutic area", "Therapeutic area by development phase", ""),
                (TWO[0][0], ROW3_Y, TWO[0][1], ROW3_H, "Trial starts per year", "New Roche-led trials by start year", ""),
                (TWO[1][0], ROW3_Y, TWO[1][1], ROW3_H, "Upcoming readouts", "Active trials with primary completion in the next 12 months", "")]),
    "04_safety": dict(
        nav=3, title="Safety <span>|</span> Pharmacovigilance",
        sub="FDA adverse event reports (FAERS / AEMS), Roche product as primary suspect, latest case version, 2020 Q1 to 2026 Q2",
        slicers=["Product", "Therapeutic area", "Year", "Reporter type"],
        kpis=["Safety cases", "Serious cases", "Fatal outcome", "Reported by HCPs", "Active PRR signals", "Product recalls"],
        panels=[(TWO[0][0], ROW2_Y, TWO[0][1], ROW2_H, "Case volume per quarter", "Cases received by the FDA, serious vs non-serious", ""),
                (TWO[1][0], ROW2_Y, TWO[1][1], ROW2_H, "Top disproportionality signals", "PRR with 95% CI (Evans criteria), indication-related terms excluded | Statistical signal, not proof of causality", ""),
                (THREE[0][0], ROW3_Y, THREE[0][1], ROW3_H, "Patient profile", "Cases by age group and sex", ""),
                (THREE[1][0], ROW3_Y, THREE[1][1], ROW3_H, "Outcome severity", "Cases by reported outcome", ""),
                (THREE[2][0], ROW3_Y, THREE[2][1], ROW3_H, "Reporter country", "Top reporting countries", "")]),
    "05_pipeline_health": dict(
        nav=4, title="Pipeline Health <span>|</span> Data platform",
        sub="Batch (GitHub Actions) and streaming (Kafka) ingestion, dbt transformations and data quality on Google Cloud",
        slicers=["Run date", "Source", "", ""],
        kpis=["Ingestion runs", "Run success rate", "dbt tests passed", "Rows ingested", "BigQuery cost (est.)", "Kafka invalid rate"],
        panels=[(TWO[0][0], ROW2_Y, TWO[0][1], ROW2_H, "Ingestion runs by source", "Rows loaded and status per run", ""),
                (TWO[1][0], ROW2_Y, TWO[1][1], ROW2_H, "Data volume by layer", "BigQuery tables per layer | FAERS (157M rows) lives in the GCS lake as external tables", ""),
                (48, ROW3_Y, 1208, ROW3_H, "Architecture", "End-to-end flow on Google Cloud, provisioned with Terraform", arch()),
                (THREE[2][0], ROW3_Y, THREE[2][1], ROW3_H, "Streaming intake (Kafka)", "Valid vs invalid events per micro-batch", "")]),
}

def cover() -> str:
    h = f"<img class='abs' src='{LOGO}' style='left:1296px;top:70px;height:236px'>"
    h += (f"<div class='abs' style='left:48px;top:200px;font-size:14px;font-weight:650;color:{T['blue']};letter-spacing:1.4px'>"
          "PORTFOLIO PROJECT | PHARMA DATA ENGINEERING</div>")
    h += "<div class='abs' style='left:48px;top:232px;font-size:60px;font-weight:700;letter-spacing:-1.2px;line-height:1.05'>Roche Pharma<br>Data Platform</div>"
    h += (f"<div class='abs' style='left:48px;top:380px;width:1020px;font-size:19px;color:{T['ink2']};line-height:1.5'>"
          "End-to-end data platform on Google Cloud built on real public data: FDA adverse event reports, "
          "Medicare drug spend and clinical trials for Roche and Genentech products.</div>")
    for i, label in enumerate(["FAERS records processed", "Roche safety cases analysed", "Clinical trials tracked"]):
        x = 48 + i * 364
        h += (f"<div class='abs card kpi' style='left:{x}px;top:500px;width:340px;height:140px'>"
              f"<div class='bar'></div><div class='l'>{label}</div></div>")
    chips = ["Terraform", "Python", "Apache Kafka", "Cloud Storage", "BigQuery", "dbt Core", "GitHub Actions", "Power BI"]
    x = 48
    for c in chips:
        w = 26 + len(c) * 9
        h += (f"<div class='abs' style='left:{x}px;top:690px;height:36px;width:{w}px;border-radius:18px;background:{T['blue_soft']};"
              f"color:{T['blue']};font-size:14px;font-weight:600;display:flex;align-items:center;justify-content:center'>{c}</div>")
        x += w + 10
    facts = [("157M", "FAERS rows in the lakehouse"), ("90+", "automated data quality tests"),
             ("0", "service account keys (keyless CI/CD)"), ("Daily", "scheduled pipeline on GitHub Actions")]
    for i, (big, small) in enumerate(facts):
        x = 48 + i * 262
        h += (f"<div class='abs' style='left:{x}px;top:770px;width:240px'><div style='font-size:30px;font-weight:700;color:{T['ink']}'>{big}</div>"
              f"<div style='font-size:13.5px;color:{T['ink2']};margin-top:4px'>{small}</div></div>")
    cards = [("Commercial", "Medicare spend 2020 to 2024, biosimilar erosion and growth brands, USD and CHF"),
             ("R&amp;D Pipeline", "Clinical trials by phase, therapeutic area, status and upcoming readouts"),
             ("Safety", "Adverse event cases, seriousness and PRR disproportionality signals"),
             ("Pipeline Health", "Runs, data quality tests, costs, data volumes and Kafka streaming")]
    for i, (name, desc) in enumerate(cards):
        x = 1180 + (i % 2) * 358; y = 350 + (i // 2) * 214
        h += (f"<div class='abs card' style='left:{x}px;top:{y}px;width:334px;height:190px'>"
              f"<div class='abs' style='left:24px;top:22px;width:36px;height:4px;border-radius:2px;background:{T['blue']}'></div>"
              f"<div class='abs' style='left:24px;top:40px;font-size:22px;font-weight:650'>{name}</div>"
              f"<div class='abs' style='left:24px;top:78px;width:286px;font-size:14px;color:{T['ink2']};line-height:1.45'>{desc}</div>"
              f"<div class='abs' style='left:24px;top:148px;font-size:14px;font-weight:650;color:{T['blue']}'>Open page &#8594;</div></div>")
    h += (f"<div class='abs' style='left:1180px;top:802px;width:692px;font-size:12.5px;color:{T['muted']};line-height:1.5'>"
          "Data sources are public and refreshed automatically. Figures are for portfolio purposes and do not represent "
          "Roche reporting. Adverse event reports do not establish causality.</div>")
    return base(h)

with sync_playwright() as p:
    browser = p.chromium.launch()
    pg = browser.new_page(viewport={"width": 1920, "height": 1080})
    docs = {"01_home": cover(), **{k: page(v) for k, v in PAGES.items()}}
    for name, html in docs.items():
        (OUT / f"{name}.html").write_text(html, encoding="utf-8")
        pg.set_content(html); pg.wait_for_timeout(300)
        pg.screenshot(path=str(OUT / f"{name}.png"))
        print("rendered", name)
    browser.close()
