{# Real Medicare spend on Roche products, in USD and converted to CHF (Roche reporting currency) at the annual average rate #}
with spending as (
    select * from {{ ref('int_cms__roche_spending') }}
),

fx as (
    select year, avg(chf_per_usd) as avg_chf_per_usd
    from {{ ref('int_fx__chf_per_usd') }}
    group by year
),

aggregated as (
    select
        product_id,
        program,
        year,
        sum(total_spending_usd) as spending_usd,
        sum(claims) as claims,
        sum(beneficiaries) as beneficiaries,
        sum(dosage_units) as dosage_units
    from spending
    group by 1, 2, 3
)

select
    {{ dbt_utils.generate_surrogate_key(['a.product_id', 'a.program', 'a.year']) }} as spending_key,
    a.product_id,
    a.program,
    a.year,
    date(a.year, 1, 1) as year_date,
    a.spending_usd,
    a.spending_usd * fx.avg_chf_per_usd as spending_chf,
    fx.avg_chf_per_usd,
    a.claims,
    a.beneficiaries,
    a.dosage_units,
    safe_divide(a.spending_usd, a.beneficiaries) as spending_per_beneficiary_usd
from aggregated as a
left join fx using (year)
