{# The Kafka consumer is at-least-once: a re-delivered batch creates duplicates, removed here by event_id #}
select
    event_id,
    source_quarter,
    received_at,
    loaded_at,
    timestamp_diff(loaded_at, received_at, second) as intake_latency_sec,
    primaryid,
    caseid,
    upper(mfr_sndr) as sender,
    reporter_country,
    patient.sex as sex,
    array_length(drugs) as drug_count,
    array_length(reactions) as reaction_count,
    array_length(outcomes) as outcome_count,
    (select {{ clean_drug_name('d.drugname') }} from unnest(drugs) d where d.role_cod = 'PS' limit 1) as ps_drugname_key,
    (select {{ clean_drug_name('d.prod_ai') }} from unnest(drugs) d where d.role_cod = 'PS' limit 1) as ps_prod_ai_key,
    array_length(outcomes) > 0 as is_serious,
    'DE' in unnest(outcomes) as is_death,
    kafka_partition,
    kafka_offset,
    batch_id
from {{ source('raw', 'faers_stream_events') }}
qualify row_number() over (partition by event_id order by loaded_at) = 1
