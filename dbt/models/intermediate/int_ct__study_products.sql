{#
  Link each study to the Roche products named in its interventions (brand or molecule, whole-word match).
  A study can test several Roche products (e.g. Tecentriq + Avastin) -> one row per study and product.
#}
with studies as (
    select nct_id, upper(interventions) as interventions_upper
    from {{ ref('stg_ct__studies') }}
    where interventions is not null
),

aliases as (
    select distinct alias, product_id
    from {{ ref('roche_product_aliases') }}
    where not regexp_contains(alias, r'[\\()]')   -- skip combination / special-character aliases
)

select
    s.nct_id,
    a.product_id,
    max(length(a.alias)) as best_alias_length
from studies as s
inner join aliases as a
    on regexp_contains(s.interventions_upper, concat(r'(^|[^A-Z0-9])', replace(a.alias, '-', r'\-'), r'([^A-Z0-9]|$)'))
group by 1, 2
