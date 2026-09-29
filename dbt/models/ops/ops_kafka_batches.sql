select
    batch_id,
    batch_ts,
    date(batch_ts) as batch_date,
    topic,
    consumer_group,
    messages,
    valid,
    invalid,
    safe_divide(invalid, messages) as invalid_rate,
    consumer_lag,
    batch_seconds,
    throughput_msg_per_sec,
    gcs_uri
from {{ source('ops', 'kafka_consumer_metrics') }}
