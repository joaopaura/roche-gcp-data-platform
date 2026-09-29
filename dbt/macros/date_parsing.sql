{# FAERS dates come as YYYYMMDD, YYYYMM or YYYY (partial dates are common in safety data) #}
{% macro parse_faers_date(column) -%}
    case length({{ column }})
        when 8 then safe.parse_date('%Y%m%d', {{ column }})
        when 6 then safe.parse_date('%Y%m%d', concat({{ column }}, '01'))
        when 4 then safe.parse_date('%Y%m%d', concat({{ column }}, '0101'))
    end
{%- endmacro %}

{# ClinicalTrials.gov dates come as YYYY-MM-DD or YYYY-MM (estimated dates) #}
{% macro parse_partial_date(column) -%}
    case length({{ column }})
        when 10 then safe.parse_date('%Y-%m-%d', {{ column }})
        when 7 then safe.parse_date('%Y-%m-%d', concat({{ column }}, '-01'))
        when 4 then safe.parse_date('%Y-%m-%d', concat({{ column }}, '-01-01'))
    end
{%- endmacro %}

{# Upper-case, trim and drop trailing dots ("RITUXIMAB." -> "RITUXIMAB") #}
{% macro clean_drug_name(column) -%}
    nullif(upper(trim(regexp_replace({{ column }}, r'\.+\s*$', ''))), '')
{%- endmacro %}
