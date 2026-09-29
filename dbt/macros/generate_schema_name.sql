{#
  dev/prod: write each layer to its own dataset (staging, intermediate, marts, ops) created by Terraform.
  ci: write everything to the auto-expiring dbt_ci dataset, so pull requests never touch real data.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if target.name == 'ci' or custom_schema_name is none -%}
        {{ target.dataset }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
