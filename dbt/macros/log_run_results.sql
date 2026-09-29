{% macro run_results_table() -%}
    `{{ target.project }}.{{ target.dataset if target.name == 'ci' else 'ops' }}.dbt_run_results`
{%- endmacro %}

{# on-run-start hook: make sure the results table exists before any model reads it #}
{% macro create_run_results_table() %}
    {% if execute %}
        {% set create_sql %}
            create table if not exists {{ run_results_table() }} (
                invocation_id string, run_started_at timestamp, target_name string,
                node_id string, resource_type string, node_name string, status string,
                failures int64, execution_time_sec float64, rows_affected int64,
                bytes_processed int64, bytes_billed int64, message string
            )
        {% endset %}
        {% do run_query(create_sql) %}
    {% endif %}
{% endmacro %}

{#
  on-run-end hook: stores the result of every model / test / seed / snapshot in ops.dbt_run_results
  (status, failures, duration, bytes processed and billed). Feeds the Pipeline Health page.
#}
{% macro log_run_results(results) %}
    {% if execute and results | length > 0 %}
        {% set table = run_results_table() %}


        {% set rows = [] %}
        {% for r in results %}
            {% set resp = r.adapter_response or {} %}
            {% set msg = (r.message or '') | string | replace('\\', ' ') | replace("'", "") | replace('\n', ' ') %}
            {% do rows.append(
                "('" ~ invocation_id ~ "', timestamp('" ~ run_started_at.strftime('%Y-%m-%d %H:%M:%S') ~ "'), '" ~ target.name ~ "', '"
                ~ r.node.unique_id ~ "', '" ~ r.node.resource_type ~ "', '" ~ r.node.name ~ "', '" ~ r.status ~ "', "
                ~ (r.failures if r.failures is not none else 'null') ~ ", " ~ (r.execution_time | round(2)) ~ ", "
                ~ (resp.get('rows_affected') if resp.get('rows_affected') is not none else 'null') ~ ", "
                ~ (resp.get('bytes_processed') if resp.get('bytes_processed') is not none else 'null') ~ ", "
                ~ (resp.get('bytes_billed') if resp.get('bytes_billed') is not none else 'null') ~ ", '"
                ~ msg[:500] ~ "')"
            ) %}
        {% endfor %}

        {% set insert_sql %}
            insert into {{ table }} values {{ rows | join(',\n') }}
        {% endset %}
        {% do run_query(insert_sql) %}
        {{ log("Logged " ~ rows | length ~ " results to " ~ table, info=True) }}
    {% endif %}
{% endmacro %}
