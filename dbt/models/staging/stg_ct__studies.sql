with source as (
    select * from {{ source('raw', 'ct_studies') }}
)

select
    nct_id,
    brief_title,
    acronym,
    overall_status,
    case
        when overall_status in ('RECRUITING', 'NOT_YET_RECRUITING', 'ACTIVE_NOT_RECRUITING', 'ENROLLING_BY_INVITATION') then 'Active'
        when overall_status = 'COMPLETED' then 'Completed'
        when overall_status in ('TERMINATED', 'WITHDRAWN', 'SUSPENDED') then 'Stopped'
        else 'Other'
    end as status_group,
    why_stopped,
    {{ parse_partial_date('start_date') }} as start_date,
    {{ parse_partial_date('primary_completion_date') }} as primary_completion_date,
    {{ parse_partial_date('completion_date') }} as completion_date,
    {{ parse_partial_date('first_post_date') }} as first_post_date,
    {{ parse_partial_date('last_update_post_date') }} as last_update_post_date,
    lead_sponsor,
    lead_sponsor_class,
    collaborators,
    regexp_contains(upper(lead_sponsor), r'ROCHE|GENENTECH|CHUGAI') as is_roche_led,
    study_type,
    nullif(phases, '') as phases,
    case nullif(phases, '')
        when 'EARLY_PHASE1' then 'Phase 1'
        when 'PHASE1' then 'Phase 1'
        when 'PHASE1|PHASE2' then 'Phase 1/2'
        when 'PHASE2' then 'Phase 2'
        when 'PHASE2|PHASE3' then 'Phase 2/3'
        when 'PHASE3' then 'Phase 3'
        when 'PHASE4' then 'Phase 4'
        else 'Not applicable'
    end as phase_group,
    case nullif(phases, '')
        when 'EARLY_PHASE1' then 1 when 'PHASE1' then 1 when 'PHASE1|PHASE2' then 2
        when 'PHASE2' then 3 when 'PHASE2|PHASE3' then 4 when 'PHASE3' then 5 when 'PHASE4' then 6
        else 7
    end as phase_sort,
    enrollment_count,
    enrollment_type,
    conditions,
    keywords,
    mesh_terms,
    intervention_types,
    interventions,
    countries,
    coalesce(array_length(split(nullif(countries, ''), '|')), 0) as country_count,
    location_count,
    has_results,
    snapshot_date
from source
