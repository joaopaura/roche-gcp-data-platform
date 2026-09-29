with source as (
    select * from {{ source('raw', 'fda_recalls') }}
)

select
    recall_number,
    event_id,
    status,
    classification,
    recalling_firm,
    product_description,
    reason_for_recall,
    case
        when regexp_contains(upper(reason_for_recall), r'STERIL') then 'Sterility assurance'
        when regexp_contains(upper(reason_for_recall), r'PARTICULATE|GLASS') then 'Particulate / foreign matter'
        when regexp_contains(upper(reason_for_recall), r'DELIVERY SYSTEM|DEVICE|IMPLANT|PEN|ADAPTER') then 'Device / delivery system'
        when regexp_contains(upper(reason_for_recall), r'STABILITY|SPECIFICATION|SUPERPOTENT|SUBPOTENT') then 'Quality specification'
        when regexp_contains(upper(reason_for_recall), r'LABEL') then 'Labelling'
        when regexp_contains(upper(reason_for_recall), r'CONTAINER|SHORT FILL|PACKAG') then 'Container / packaging'
        else 'Other'
    end as reason_category,
    voluntary_mandated,
    distribution_pattern,
    {{ parse_faers_date('recall_initiation_date') }} as recall_initiation_date,
    {{ parse_faers_date('center_classification_date') }} as classification_date,
    {{ parse_faers_date('termination_date') }} as termination_date,
    {{ clean_drug_name("split(coalesce(brand_names, ''), '|')[safe_offset(0)]") }} as brand_key,
    brand_names,
    generic_names
from source
