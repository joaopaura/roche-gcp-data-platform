{# Adverse event intake received through Kafka (streaming replay), mapped to Roche products #}
with events as (
    select * from {{ ref('stg_faers__stream_events') }}
),

aliases as (
    select alias, product_id from {{ ref('roche_product_aliases') }}
)

select
    e.event_id,
    e.received_at,
    date(e.received_at) as received_date,
    e.loaded_at,
    e.intake_latency_sec,
    e.caseid,
    e.primaryid,
    coalesce(by_name.product_id, by_ingredient.product_id) as product_id,
    e.reporter_country,
    e.sex,
    e.drug_count,
    e.reaction_count,
    e.is_serious,
    e.is_death,
    e.kafka_partition,
    e.batch_id
from events as e
left join aliases as by_name on by_name.alias = e.ps_drugname_key
left join aliases as by_ingredient on by_ingredient.alias = e.ps_prod_ai_key
qualify row_number() over (partition by e.event_id order by by_name.product_id is null) = 1
