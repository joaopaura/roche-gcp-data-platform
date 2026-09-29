select
    product_id,
    brand_name,
    molecule,
    therapeutic_area,
    modality,
    us_approval_year,
    generic_or_biosimilar_us_entry_year,
    us_partner,
    case
        when generic_or_biosimilar_us_entry_year is not null then 'Loss of exclusivity'
        when us_approval_year >= 2016 then 'Growth (launched 2016+)'
        else 'Established'
    end as portfolio_segment,
    generic_or_biosimilar_us_entry_year is not null as faces_biosimilar_or_generic
from {{ ref('roche_products') }}
