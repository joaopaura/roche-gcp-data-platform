select
    primaryid,
    caseid,
    upper(trim(outc_cod)) as outc_cod,
    quarter
from {{ source('raw', 'faers_outc') }}
