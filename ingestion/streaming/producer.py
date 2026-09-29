"""Kafka producer: replays real FAERS cases submitted by Roche / Genentech as a live intake stream.

Reads one quarter from the bronze layer, keeps cases whose manufacturer sender is Roche,
Genentech, Hoffmann-La Roche or Chugai, builds one nested JSON event per case and publishes it to
topic 'adverse-event-intake' (key = caseid, so all versions of a case keep their order).
A small share of events is broken on purpose (--error-rate) to demonstrate the dead-letter queue.

Run:  python -m ingestion.streaming.producer --quarter 2026Q2 --rate 50 --limit 5000
"""
import argparse
import json
import random
import tempfile
import time
from pathlib import Path

import pandas as pd
from confluent_kafka import Producer

from ingestion.common import config, gcs
from ingestion.common.logger import get_logger
from ingestion.streaming.events import CASE_FIELDS, DRUG_FIELDS, PATIENT_FIELDS, build_event, inject_fault

TOPIC = "adverse-event-intake"
ROCHE_SENDERS = r"ROCHE|GENENTECH|HOFFMANN|CHUGAI"

logger = get_logger("producer")


def read_bronze(table: str, quarter: str, columns: list[str]) -> pd.DataFrame:
    blob = gcs.lake_path("bronze", "faers", table, f"quarter={quarter}", f"{table}.parquet")
    with tempfile.TemporaryDirectory() as tmp:
        local = gcs.download_file(blob, Path(tmp) / f"{table}.parquet")
        return pd.read_parquet(local, columns=columns)


def load_roche_cases(quarter: str) -> list[dict]:
    demo = read_bronze("demo", quarter, list(dict.fromkeys(CASE_FIELDS + PATIENT_FIELDS)))
    demo = demo[demo["mfr_sndr"].str.contains(ROCHE_SENDERS, case=False, na=False)]
    ids = set(demo["primaryid"])
    logger.info("%s: %s cases sent by Roche group companies", quarter, f"{len(ids):,}")

    drug = read_bronze("drug", quarter, ["primaryid"] + DRUG_FIELDS)
    reac = read_bronze("reac", quarter, ["primaryid", "pt"])
    outc = read_bronze("outc", quarter, ["primaryid", "outc_cod"])
    drug, reac, outc = (df[df["primaryid"].isin(ids)] for df in (drug, reac, outc))

    drugs_by_case = {pid: g[DRUG_FIELDS].to_dict("records") for pid, g in drug.groupby("primaryid")}
    reac_by_case = reac.groupby("primaryid")["pt"].apply(list).to_dict()
    outc_by_case = outc.groupby("primaryid")["outc_cod"].apply(list).to_dict()

    return [
        {"case": case, "drugs": drugs_by_case.get(case["primaryid"], []),
         "reactions": reac_by_case.get(case["primaryid"], []),
         "outcomes": outc_by_case.get(case["primaryid"], [])}
        for case in demo.to_dict("records")
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay FAERS Roche cases into Kafka")
    parser.add_argument("--quarter", default="2026Q2")
    parser.add_argument("--rate", type=float, default=50, help="Events per second (0 = as fast as possible)")
    parser.add_argument("--limit", type=int, default=0, help="Max events (0 = all)")
    parser.add_argument("--error-rate", type=float, default=0.02, help="Share of events broken on purpose")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    cases = load_roche_cases(args.quarter.upper())
    if args.limit:
        cases = cases[: args.limit]

    producer = Producer({
        "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
        "client.id": "faers-replay-producer",
        "acks": "all",
        "enable.idempotence": True,
        "compression.type": "lz4",
        "linger.ms": 50,
    })
    stats = {"delivered": 0, "failed": 0, "faulty": 0}

    def on_delivery(err, msg):
        stats["failed" if err else "delivered"] += 1
        if err:
            logger.error("Delivery failed: %s", err)

    start = time.perf_counter()
    for i, item in enumerate(cases, start=1):
        event = build_event(item["case"], item["drugs"], item["reactions"], item["outcomes"], args.quarter.upper())
        if rng.random() < args.error_rate:
            event = inject_fault(event, rng)
            stats["faulty"] += 1

        while True:
            try:
                producer.produce(TOPIC, key=str(event.get("caseid")), value=json.dumps(event).encode("utf-8"),
                                 on_delivery=on_delivery)
                break
            except BufferError:  # local queue full: wait for deliveries, then retry
                producer.poll(1)
        producer.poll(0)

        if i % 1000 == 0:
            logger.info("Sent %s / %s events", f"{i:,}", f"{len(cases):,}")
        if args.rate > 0:
            time.sleep(1 / args.rate)

    producer.flush(30)
    elapsed = time.perf_counter() - start
    logger.info("Done: %s delivered | %s failed | %s faulty on purpose | %.0fs (%.1f events/s)",
                stats["delivered"], stats["failed"], stats["faulty"], elapsed, stats["delivered"] / max(elapsed, 1))


if __name__ == "__main__":
    main()
