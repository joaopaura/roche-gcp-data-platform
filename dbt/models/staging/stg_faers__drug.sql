select
    primaryid,
    caseid,
    safe_cast(drug_seq as int64) as drug_seq,
    role_cod,
    {{ clean_drug_name('drugname') }} as drugname_key,
    {{ clean_drug_name('prod_ai') }} as prod_ai_key,
    route,
    quarter
from {{ source('raw', 'faers_drug') }}
