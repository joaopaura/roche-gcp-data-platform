{{ config(materialized='table') }}
{# Row counts and storage per dataset and table (medallion layers). External tables store data in GCS, so size = 0 here. #}
{% set datasets = ['raw', 'staging', 'intermediate', 'marts', 'ops'] %}

{% for ds in datasets %}
select
    '{{ ds }}' as layer,
    table_id,
    case type when 1 then 'table' when 2 then 'view' when 3 then 'external' else 'other' end as table_type,
    row_count,
    size_bytes,
    round(size_bytes / pow(1024, 2), 2) as size_mb,
    timestamp_millis(last_modified_time) as last_modified_at,
    current_timestamp() as measured_at
from `{{ target.project }}.{{ ds }}.__TABLES__`
{% if not loop.last %}union all{% endif %}
{% endfor %}
