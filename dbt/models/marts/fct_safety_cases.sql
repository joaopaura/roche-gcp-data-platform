{{ config(cluster_by=['product_id']) }}
{# One row per latest FAERS case and Roche primary-suspect product, with patient profile and seriousness #}
with roche_cases as (
    select * from {{ ref('int_faers__roche_ps_drugs') }}
),

demo as (
    select *
    from {{ ref('stg_faers__demo') }}
    where primaryid in (select primaryid from roche_cases)
    qualify row_number() over (partition by primaryid order by quarter desc) = 1
),

outcomes as (
    select
        primaryid,
        string_agg(distinct outc_cod, '|' order by outc_cod) as outcome_codes,
        logical_or(outc_cod = 'DE') as is_death,
        logical_or(outc_cod = 'LT') as is_life_threatening,
        logical_or(outc_cod = 'HO') as is_hospitalisation
    from {{ ref('stg_faers__outc') }}
    where primaryid in (select primaryid from roche_cases)
    group by primaryid
),

reactions as (
    select primaryid, count(distinct reaction_pt) as reaction_count
    from {{ ref('stg_faers__reac') }}
    where primaryid in (select primaryid from roche_cases)
    group by primaryid
),

occupations as (
    select * from {{ ref('faers_occupation_codes') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['rc.primaryid', 'rc.product_id']) }} as safety_case_key,
    rc.primaryid,
    d.caseid,
    d.caseversion,
    rc.product_id,
    rc.match_method,
    d.quarter,
    d.fda_date,
    d.init_fda_date,
    d.event_date,
    d.report_type,
    case d.report_type
        when 'EXP' then 'Expedited (15-day)'
        when 'PER' then 'Periodic'
        when 'DIR' then 'Direct'
        else 'Other'
    end as report_type_label,
    d.is_roche_sender,
    coalesce(o.reporter_type, 'Unknown') as reporter_type,
    coalesce(o.is_health_professional, false) as is_health_professional_report,
    d.reporter_country,
    d.occurrence_country,
    d.sex,
    case when d.age_years between 0 and 120 then d.age_years end as age_years,
    case
        when d.age_years is null or d.age_years > 120 then 'Unknown'
        when d.age_years < 18 then '0-17'
        when d.age_years < 45 then '18-44'
        when d.age_years < 65 then '45-64'
        when d.age_years < 75 then '65-74'
        else '75+'
    end as age_group,
    case when d.weight_kg between 1 and 350 then d.weight_kg end as weight_kg,
    oc.outcome_codes,
    oc.outcome_codes is not null as is_serious,
    coalesce(oc.is_death, false) as is_death,
    coalesce(oc.is_life_threatening, false) as is_life_threatening,
    coalesce(oc.is_hospitalisation, false) as is_hospitalisation,
    coalesce(r.reaction_count, 0) as reaction_count
from roche_cases as rc
inner join demo as d using (primaryid)
left join outcomes as oc using (primaryid)
left join reactions as r using (primaryid)
left join occupations as o on o.occp_cod = d.occp_cod
