{# Number of (latest) cases reporting each reaction across the WHOLE database: the PRR comparator #}
with latest as (
    select primaryid from {{ ref('int_faers__latest_cases') }}
),

case_reactions as (
    select distinct r.primaryid, r.reaction_pt
    from {{ ref('stg_faers__reac') }} as r
    inner join latest using (primaryid)
)

select
    reaction_pt,
    count(*) as cases_with_reaction
from case_reactions
group by reaction_pt
