{# Results of dbt models / tests written by the on-run-end hook (macro log_run_results) #}
select
    invocation_id,
    run_started_at,
    date(run_started_at) as run_date,
    target_name,
    node_id,
    resource_type,
    node_name,
    status,
    failures,
    execution_time_sec,
    rows_affected,
    bytes_processed,
    bytes_billed,
    round(bytes_billed / pow(1024, 4) * 6.25, 4) as estimated_cost_usd,
    message
from {{ run_results_table() }}
