"""Kafka consumer: validates intake events, routes bad ones to a dead-letter topic and loads
good ones to the lake + BigQuery in micro-batches.

Delivery guarantee: at-least-once. Offsets are committed only AFTER the batch is safely in GCS and
BigQuery, so a crash can re-deliver a batch (duplicates are removed in dbt by event_id).

Every batch writes metrics (volume, invalid events, consumer lag, throughput) to
ops.kafka_consumer_metrics for the Pipeline Health page.

Run:  python -m ingestion.streaming.consumer --idle-timeout 60
"""
import argparse
import gzip
import json
import time
import uuid
from datetime import date, datetime, timezone

from confluent_kafka import Consumer, Producer
from google.cloud import bigquery

from ingestion.common import bq, config, gcs
from ingestion.common.logger import get_logger
from ingestion.common.run_tracker import track_run
from ingestion.streaming.events import BQ_SCHEMA, validate_event

TOPIC = "adverse-event-intake"
DLQ_TOPIC = "adverse-event-dlq"
GROUP_ID = "pv-intake-loader"

METRICS_SCHEMA = [
    bigquery.SchemaField("batch_id", "STRING"),
    bigquery.SchemaField("batch_ts", "TIMESTAMP"),
    bigquery.SchemaField("topic", "STRING"),
    bigquery.SchemaField("consumer_group", "STRING"),
    bigquery.SchemaField("messages", "INTEGER"),
    bigquery.SchemaField("valid", "INTEGER"),
    bigquery.SchemaField("invalid", "INTEGER"),
    bigquery.SchemaField("consumer_lag", "INTEGER"),
    bigquery.SchemaField("batch_seconds", "FLOAT"),
    bigquery.SchemaField("throughput_msg_per_sec", "FLOAT"),
    bigquery.SchemaField("gcs_uri", "STRING"),
]

logger = get_logger("consumer")


def consumer_lag(consumer: Consumer) -> int:
    """Messages still waiting in the topic for this consumer group (sum over partitions)."""
    total = 0
    for tp in consumer.assignment():
        low, high = consumer.get_watermark_offsets(tp, timeout=5)
        position = consumer.position([tp])[0].offset
        total += max(high - (position if position >= 0 else low), 0)
    return total


def send_to_dlq(dlq: Producer, msg, errors: list[str]) -> None:
    dlq.produce(
        DLQ_TOPIC,
        key=msg.key(),
        value=msg.value(),
        headers={
            "error": "; ".join(errors),
            "source_topic": msg.topic(),
            "source_partition": str(msg.partition()),
            "source_offset": str(msg.offset()),
        },
    )
    dlq.poll(0)


def flush_batch(buffer: list[dict], invalid: int, started: float, consumer: Consumer, dlq: Producer, run: dict) -> None:
    if not buffer and not invalid:
        return
    batch_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}_{uuid.uuid4().hex[:6]}"
    loaded_at = datetime.now(timezone.utc).isoformat()
    uri = None

    if buffer:
        for event in buffer:
            event["batch_id"] = batch_id
            event["loaded_at"] = loaded_at
        payload = gzip.compress("\n".join(json.dumps(e) for e in buffer).encode("utf-8"))
        blob = gcs.lake_path("bronze", "faers_stream", f"ingest_date={date.today().isoformat()}", f"batch_{batch_id}.jsonl.gz")
        uri = gcs.upload_bytes(payload, blob, "application/gzip")
        bq.load_json_from_gcs(uri, "faers_stream_events", BQ_SCHEMA, partition_field="received_at")
        run["files_written"] += 1
        run["bytes_written"] += len(payload)

    dlq.flush(10)
    consumer.commit(asynchronous=False)  # commit only after data is safe (at-least-once)

    seconds = time.monotonic() - started
    messages = len(buffer) + invalid
    lag = consumer_lag(consumer)
    bq.append_rows([{
        "batch_id": batch_id,
        "batch_ts": loaded_at,
        "topic": TOPIC,
        "consumer_group": GROUP_ID,
        "messages": messages,
        "valid": len(buffer),
        "invalid": invalid,
        "consumer_lag": lag,
        "batch_seconds": round(seconds, 2),
        "throughput_msg_per_sec": round(messages / max(seconds, 0.001), 1),
        "gcs_uri": uri,
    }], "kafka_consumer_metrics", METRICS_SCHEMA)

    run["rows_loaded"] += len(buffer)
    logger.info("Batch %s | %s valid | %s invalid -> DLQ | lag %s | %.1fs", batch_id, len(buffer), invalid, lag, seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Consume adverse event intake stream")
    parser.add_argument("--batch-size", type=int, default=1000, help="Flush after N valid events")
    parser.add_argument("--flush-seconds", type=int, default=60, help="Flush at least every N seconds")
    parser.add_argument("--idle-timeout", type=int, default=0, help="Stop after N seconds without messages (0 = run forever)")
    args = parser.parse_args()

    consumer = Consumer({
        "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
        "group.id": GROUP_ID,
        "client.id": "pv-intake-consumer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    dlq = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS, "client.id": "pv-intake-dlq", "acks": "all"})
    consumer.subscribe([TOPIC])
    logger.info("Listening to '%s' as group '%s' (Ctrl+C to stop)", TOPIC, GROUP_ID)

    with track_run("kafka_consumer") as run:
        buffer, invalid = [], 0
        batch_started = last_message = time.monotonic()
        try:
            while True:
                msg = consumer.poll(1.0)
                now = time.monotonic()

                if msg is None:
                    if (buffer or invalid) and now - batch_started >= args.flush_seconds:
                        flush_batch(buffer, invalid, batch_started, consumer, dlq, run)
                        buffer, invalid, batch_started = [], 0, time.monotonic()
                    if args.idle_timeout and now - last_message >= args.idle_timeout:
                        logger.info("No messages for %ss, stopping", args.idle_timeout)
                        break
                    continue

                if msg.error():
                    logger.error("Kafka error: %s", msg.error())
                    continue

                last_message = now
                try:
                    event = json.loads(msg.value())
                    errors = validate_event(event)
                except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                    event, errors = None, ["invalid json"]

                if errors:
                    send_to_dlq(dlq, msg, errors)
                    invalid += 1
                else:
                    event["kafka_partition"] = msg.partition()
                    event["kafka_offset"] = msg.offset()
                    buffer.append(event)

                if len(buffer) >= args.batch_size or now - batch_started >= args.flush_seconds:
                    flush_batch(buffer, invalid, batch_started, consumer, dlq, run)
                    buffer, invalid, batch_started = [], 0, time.monotonic()
        except KeyboardInterrupt:
            logger.info("Stopping (Ctrl+C)")
        finally:
            flush_batch(buffer, invalid, batch_started, consumer, dlq, run)
            consumer.close()
        run["target"] = "raw.faers_stream_events"


if __name__ == "__main__":
    main()
