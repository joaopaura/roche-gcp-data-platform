{#
  Disproportionality analysis (PRR, Evans et al. 2001) per Roche product and MedDRA reaction.

                        reaction    other reactions
    Roche product          a              b
    all other drugs        c              d

  PRR = [a / (a + b)] / [c / (c + d)]   | signal when a >= 3, PRR >= 2 and chi-square (Yates) >= 4
  A statistical signal is a hypothesis for medical review, not proof of causality.
#}
with product_reaction as (
    select * from {{ ref('int_faers__product_reaction_counts') }}
),

product_totals as (
    select product_id, count(distinct primaryid) as product_cases
    from {{ ref('int_faers__roche_ps_drugs') }}
    group by product_id
),

background as (
    select * from {{ ref('int_faers__event_background') }}
),

database_total as (
    select count(*) as total_cases from {{ ref('int_faers__latest_cases') }}
),

cells as (
    select
        pr.product_id,
        pr.reaction_pt,
        cast(pr.cases as float64) as a,
        cast(pt.product_cases - pr.cases as float64) as b,
        cast(bg.cases_with_reaction - pr.cases as float64) as c,
        cast(dt.total_cases - pt.product_cases - (bg.cases_with_reaction - pr.cases) as float64) as d
    from product_reaction as pr
    inner join product_totals as pt using (product_id)
    inner join background as bg using (reaction_pt)
    cross join database_total as dt
    where pr.cases >= {{ var('prr_min_cases') }}
),

stats as (
    select
        *,
        a + b + c + d as n,
        safe_divide(a / (a + b), safe_divide(c, c + d)) as prr,
        sqrt(safe_divide(1, a) - safe_divide(1, a + b) + safe_divide(1, c) - safe_divide(1, c + d)) as se_log_prr,
        safe_divide(
            (a + b + c + d) * pow(greatest(abs(a * d - b * c) - (a + b + c + d) / 2, 0), 2),
            (a + b) * (c + d) * (a + c) * (b + d)
        ) as chi_square
    from cells
)

select
    {{ dbt_utils.generate_surrogate_key(['product_id', 'reaction_pt']) }} as signal_key,
    product_id,
    reaction_pt,
    cast(a as int64) as cases_product_reaction,
    cast(a + b as int64) as cases_product,
    cast(a + c as int64) as cases_reaction_all_drugs,
    safe_divide(a, a + b) as reporting_rate,
    prr,
    exp(safe.ln(prr) - 1.96 * se_log_prr) as prr_lower_95,
    exp(safe.ln(prr) + 1.96 * se_log_prr) as prr_upper_95,
    chi_square,
    a >= {{ var('prr_min_cases') }} and prr >= {{ var('prr_threshold') }} and chi_square >= {{ var('chi_square_threshold') }}
        as is_signal,
    rank() over (partition by product_id order by a desc) as rank_by_cases
from stats
where c > 0
