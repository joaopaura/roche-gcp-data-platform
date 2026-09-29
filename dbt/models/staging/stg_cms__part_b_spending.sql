with source as (
    select * from {{ source('raw', 'cms_part_b') }}
),

unpivoted as (
    {% for year in var('cms_years') %}
    select
        trim(HCPCS_Cd) as hcpcs_code,
        trim(HCPCS_Desc) as hcpcs_description,
        trim(replace(Brnd_Name, '*', '')) as brand_name,
        trim(Gnrc_Name) as generic_name,
        cast(null as string) as manufacturer,
        {{ year }} as year,
        safe_cast(Tot_Spndng_{{ year }} as numeric) as total_spending_usd,
        safe_cast(Tot_Dsg_Unts_{{ year }} as numeric) as dosage_units,
        safe_cast(Tot_Clms_{{ year }} as numeric) as claims,
        safe_cast(Tot_Benes_{{ year }} as numeric) as beneficiaries,
        Outlier_Flag_{{ year }} = '1' as is_outlier
    from source
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)

select
    'Part B' as program,
    {{ clean_drug_name('brand_name') }} as brand_key,
    *
from unpivoted
where total_spending_usd is not null
