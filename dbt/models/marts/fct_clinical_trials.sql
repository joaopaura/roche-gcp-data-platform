with studies as (
    select * from {{ ref('stg_ct__studies') }}
),

study_products as (
    select * from {{ ref('int_ct__study_products') }}
),

primary_product as (
    select nct_id, product_id, count(*) over (partition by nct_id) as roche_product_count
    from study_products
    qualify row_number() over (partition by nct_id order by best_alias_length desc, product_id) = 1
),

products as (
    select product_id, brand_name, therapeutic_area from {{ ref('roche_products') }}
)

select
    s.nct_id,
    s.brief_title,
    s.acronym,
    pp.product_id as primary_product_id,
    coalesce(p.brand_name, 'No marketed Roche product') as primary_product_brand,
    coalesce(pp.roche_product_count, 0) as roche_product_count,
    coalesce(p.therapeutic_area, {{ therapeutic_area_from_text("concat(coalesce(s.mesh_terms, ''), ' ', coalesce(s.conditions, ''))") }}) as therapeutic_area,
    s.overall_status,
    s.status_group,
    s.why_stopped,
    s.phase_group,
    s.phase_sort,
    s.study_type,
    s.is_roche_led,
    if(s.is_roche_led, 'Roche-led', 'Collaboration') as sponsor_role,
    s.lead_sponsor,
    s.start_date,
    s.primary_completion_date,
    s.completion_date,
    s.last_update_post_date,
    extract(year from s.start_date) as start_year,
    date_diff(coalesce(s.primary_completion_date, s.completion_date), s.start_date, month) as planned_duration_months,
    s.status_group = 'Active' and s.primary_completion_date between current_date() and date_add(current_date(), interval 12 month)
        as readout_next_12_months,
    s.enrollment_count,
    s.enrollment_type,
    s.country_count,
    s.location_count,
    s.has_results,
    s.conditions,
    s.snapshot_date
from studies as s
left join primary_product as pp using (nct_id)
left join products as p on p.product_id = pp.product_id
