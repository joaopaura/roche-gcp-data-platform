select
    rate_date,
    currency,
    base_currency,
    rate
from {{ source('raw', 'ecb_fx_rates') }}
where rate is not null
