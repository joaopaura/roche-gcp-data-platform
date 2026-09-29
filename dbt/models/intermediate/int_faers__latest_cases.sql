{{ config(cluster_by=['primaryid']) }}
{#
  FDA rule: a case (caseid) can be submitted several times (follow-ups). Only the latest version
  counts, otherwise the same patient event is counted more than once (~18% of reports are older versions).
  Kept slim on purpose: this table is the denominator for disproportionality (PRR).
#}
select
    primaryid,
    caseid,
    caseversion,
    quarter,
    fda_date,
    is_roche_sender
from {{ ref('stg_faers__demo') }}
where fda_date is not null
qualify row_number() over (
    partition by caseid
    order by caseversion desc, fda_date desc, primaryid desc
) = 1
