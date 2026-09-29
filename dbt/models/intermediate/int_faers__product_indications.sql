{#
  Main indications per Roche product (indication of the primary suspect drug, >= 1% of the product cases).
  Used to flag "confounding by indication": the treated disease reported as if it were an adverse event
  (e.g. "Multiple Sclerosis" for Ocrevus).
#}
with ps as (
    select primaryid, product_id, drug_seq from {{ ref('int_faers__roche_ps_drugs') }}
),

indications as (
    select primaryid, drug_seq, indication_pt
    from {{ ref('stg_faers__indi') }}
    where primaryid in (select primaryid from ps)
      and indication_pt not in ('Product Used For Unknown Indication', 'Off Label Use')
),

counts as (
    select ps.product_id, i.indication_pt, count(distinct ps.primaryid) as cases
    from ps
    inner join indications as i on i.primaryid = ps.primaryid and i.drug_seq = ps.drug_seq
    group by 1, 2
),

totals as (
    select product_id, count(distinct primaryid) as product_cases from ps group by 1
)

select
    c.product_id,
    c.indication_pt,
    c.cases,
    safe_divide(c.cases, t.product_cases) as share_of_product_cases
from counts as c
inner join totals as t using (product_id)
where safe_divide(c.cases, t.product_cases) >= 0.01
