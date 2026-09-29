with areas as (
    select therapeutic_area from {{ ref('roche_products') }}
    union distinct
    select therapeutic_area from {{ ref('fct_clinical_trials') }}
)

select
    therapeutic_area,
    case therapeutic_area
        when 'Oncology' then 1 when 'Neuroscience' then 2 when 'Immunology' then 3
        when 'Ophthalmology' then 4 when 'Haematology' then 5 when 'Respiratory' then 6
        when 'Infectious Diseases' then 7 when 'Cardiovascular' then 8
        when 'Metabolism & Endocrinology' then 9 else 99
    end as sort_order
from areas
where therapeutic_area is not null
