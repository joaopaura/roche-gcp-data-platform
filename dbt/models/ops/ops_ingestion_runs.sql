{# Python ingestion runs, flagging runs that overlapped a previous run of the same source (no concurrency lock) #}
with runs as (
    select * from {{ source('ops', 'ingestion_runs') }}
)

select
    r.run_id,
    r.source,
    r.status,
    r.started_at,
    r.finished_at,
    date(r.started_at) as run_date,
    r.duration_sec,
    r.rows_loaded,
    r.files_written,
    r.bytes_written,
    r.target,
    r.triggered_by,
    r.error_message,
    exists (
        select 1 from runs as o
        where o.source = r.source
          and o.run_id != r.run_id
          and o.started_at < r.started_at
          and o.finished_at > r.started_at
    ) as overlapped_previous_run
from runs as r
