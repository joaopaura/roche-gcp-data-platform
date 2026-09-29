{# ECB publishes rates against EUR: CHF per USD = (CHF per EUR) / (USD per EUR) #}
with pivoted as (
    select
        rate_date,
        max(if(currency = 'USD', rate, null)) as usd_per_eur,
        max(if(currency = 'CHF', rate, null)) as chf_per_eur
    from {{ ref('stg_ecb__fx_rates') }}
    group by rate_date
)

select
    rate_date,
    extract(year from rate_date) as year,
    usd_per_eur,
    chf_per_eur,
    chf_per_eur / usd_per_eur as chf_per_usd
from pivoted
where usd_per_eur is not null and chf_per_eur is not null
