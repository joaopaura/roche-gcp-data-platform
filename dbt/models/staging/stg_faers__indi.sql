select
    primaryid,
    caseid,
    safe_cast(indi_drug_seq as int64) as drug_seq,
    initcap(trim(indi_pt)) as indication_pt,
    quarter
from {{ source('raw', 'faers_indi') }}
where nullif(trim(indi_pt), '') is not null
