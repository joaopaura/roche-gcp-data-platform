with recalls as (
    select * from {{ ref('stg_fda__recalls') }}
),

aliases as (
    select alias, product_id from {{ ref('roche_product_aliases') }} where alias_type = 'brand'
)

select
    r.recall_number,
    coalesce(a.product_id, desc_match.product_id) as product_id,
    r.classification,
    r.status,
    r.reason_category,
    r.reason_for_recall,
    r.product_description,
    r.voluntary_mandated,
    r.recall_initiation_date,
    r.classification_date,
    r.termination_date,
    extract(year from r.recall_initiation_date) as recall_year
from recalls as r
left join aliases as a on a.alias = r.brand_key
left join aliases as desc_match
    on a.product_id is null
    and regexp_contains(upper(r.product_description), concat(r'(^|[^A-Z])', desc_match.alias, r'([^A-Z]|$)'))
qualify row_number() over (partition by r.recall_number order by length(desc_match.alias) desc) = 1
