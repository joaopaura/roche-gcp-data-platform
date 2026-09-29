{# One row per report version. Deduplication to the latest case version happens in intermediate. #}
with source as (
    select * from {{ source('raw', 'faers_demo') }}
),

typed as (
    select
        primaryid,
        caseid,
        safe_cast(caseversion as int64) as caseversion,
        quarter,
        {{ parse_faers_date('fda_dt') }} as fda_date,
        {{ parse_faers_date('init_fda_dt') }} as init_fda_date,
        {{ parse_faers_date('event_dt') }} as event_date,
        rept_cod as report_type,
        upper(trim(mfr_sndr)) as sender,
        coalesce(regexp_contains(upper(mfr_sndr), r'{{ var("roche_senders_regex") }}'), false) as is_roche_sender,
        nullif(occp_cod, '') as occp_cod,
        nullif(reporter_country, '') as reporter_country,
        nullif(occr_country, '') as occurrence_country,
        nullif(sex, '') as sex,
        safe_cast(age as float64) as age_value,
        age_cod,
        safe_cast(wt as float64) as weight_value,
        wt_cod
    from source
)

select
    * except (age_value, age_cod, weight_value, wt_cod),
    case
        when age_cod = 'YR' then age_value
        when age_cod = 'MON' then age_value / 12
        when age_cod = 'WK' then age_value / 52
        when age_cod = 'DY' then age_value / 365
        when age_cod = 'HR' then age_value / 8760
        when age_cod = 'DEC' then age_value * 10
    end as age_years,
    case
        when wt_cod = 'KG' then weight_value
        when wt_cod = 'LBS' then weight_value * 0.453592
        when wt_cod = 'GMS' then weight_value / 1000
    end as weight_kg
from typed
