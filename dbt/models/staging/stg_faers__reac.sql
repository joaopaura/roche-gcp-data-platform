select
    primaryid,
    caseid,
    initcap(trim(pt)) as reaction_pt,
    quarter
from {{ source('raw', 'faers_reac') }}
where nullif(trim(pt), '') is not null
