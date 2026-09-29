{{ config(cluster_by=['product_id']) }}
{#
  Attribute each latest case to a Roche product when the PRIMARY SUSPECT drug is a Roche product.
  1. match on the reported drug name (brand names are unambiguous), else on the active ingredient
  2. generic names shared with biosimilars / generics (e.g. RITUXIMAB, BEVACIZUMAB) only count when the
     case was sent by a Roche group company (requires_roche_sender = true)
#}
with latest as (
    select primaryid, is_roche_sender
    from {{ ref('int_faers__latest_cases') }}
),

primary_suspect as (
    select primaryid, drug_seq, drugname_key, prod_ai_key
    from {{ ref('stg_faers__drug') }}
    where role_cod = 'PS'
),

aliases as (
    select alias, product_id, requires_roche_sender
    from {{ ref('roche_product_aliases') }}
),

matched as (
    select
        ps.primaryid,
        ps.drug_seq,
        ps.drugname_key,
        ps.prod_ai_key,
        latest.is_roche_sender,
        coalesce(by_name.product_id, by_ingredient.product_id) as product_id,
        if(by_name.product_id is not null, 'drug name', 'active ingredient') as match_method,
        coalesce(by_name.requires_roche_sender, by_ingredient.requires_roche_sender) as requires_roche_sender
    from primary_suspect as ps
    inner join latest using (primaryid)
    left join aliases as by_name on by_name.alias = ps.drugname_key
    left join aliases as by_ingredient on by_ingredient.alias = ps.prod_ai_key
)

select
    primaryid,
    product_id,
    drug_seq,
    drugname_key,
    prod_ai_key,
    match_method,
    is_roche_sender
from matched
where product_id is not null
  and (not requires_roche_sender or is_roche_sender)
qualify row_number() over (partition by primaryid, product_id order by drug_seq) = 1
