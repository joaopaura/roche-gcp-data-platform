{# Cases per Roche product and reaction (cell "a" of the 2x2 disproportionality table) #}
with product_cases as (
    select distinct primaryid, product_id
    from {{ ref('int_faers__roche_ps_drugs') }}
),

case_reactions as (
    select distinct r.primaryid, r.reaction_pt
    from {{ ref('stg_faers__reac') }} as r
    where r.primaryid in (select primaryid from product_cases)
)

select
    pc.product_id,
    cr.reaction_pt,
    count(distinct pc.primaryid) as cases
from product_cases as pc
inner join case_reactions as cr using (primaryid)
group by 1, 2
