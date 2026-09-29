{#
  Roche products in Medicare:
  - Part D (pharmacy): the file has a manufacturer column -> keep Genentech / Roche rows, match brand
  - Part B (physician-administered infusions like Ocrevus, Tecentriq): no manufacturer column -> brand match only
    (biosimilars have their own brand names, so a brand match is always the Roche product)
#}
with brand_aliases as (
    select alias, product_id
    from {{ ref('roche_product_aliases') }}
    where alias_type = 'brand'
),

part_d as (
    select program, brand_key, brand_name, generic_name, manufacturer, cast(null as string) as hcpcs_code,
           year, total_spending_usd, dosage_units, claims, beneficiaries, is_outlier
    from {{ ref('stg_cms__part_d_spending') }}
    where regexp_contains(upper(manufacturer), r'^(GENENTECH|ROCHE|HOFFMANN)')
),

part_b as (
    select program, brand_key, brand_name, generic_name, manufacturer, hcpcs_code,
           year, total_spending_usd, dosage_units, claims, beneficiaries, is_outlier
    from {{ ref('stg_cms__part_b_spending') }}
),

unioned as (
    select * from part_d
    union all
    select * from part_b
)

select
    a.product_id,
    u.*
from unioned as u
inner join brand_aliases as a on a.alias = u.brand_key
