{# Rule-based therapeutic area from MeSH terms / conditions (used when no Roche product is matched) #}
{% macro therapeutic_area_from_text(column) -%}
    case
        when regexp_contains(upper({{ column }}), r'NEOPLASM|CARCINOMA|CANCER|LYMPHOMA|LEUKEMIA|LEUKAEMIA|MYELOMA|MELANOMA|TUMOR|TUMOUR|SARCOMA|GLIOBLASTOMA|GLIOMA|MESOTHELIOMA') then 'Oncology'
        when regexp_contains(upper({{ column }}), r'HEMOPHILIA|HAEMOPHILIA|ANEMIA|ANAEMIA|HEMOGLOBINURIA|THROMBOCYTOPENI|SICKLE CELL|VON WILLEBRAND') then 'Haematology'
        when regexp_contains(upper({{ column }}), r'MULTIPLE SCLEROSIS|SPINAL MUSCULAR|ALZHEIMER|PARKINSON|HUNTINGTON|NEUROMYELITIS|AUTIS|EPILEP|DUCHENNE|MYASTHENIA|NERVOUS SYSTEM') then 'Neuroscience'
        when regexp_contains(upper({{ column }}), r'MACULAR|RETIN|UVEITIS|EYE DISEASE|VISION|GEOGRAPHIC ATROPHY') then 'Ophthalmology'
        when regexp_contains(upper({{ column }}), r'INFLUENZA|HIV|HEPATITIS|COVID|SARS-COV|INFECTION|CYTOMEGALOVIRUS|SEPSIS') then 'Infectious Diseases'
        when regexp_contains(upper({{ column }}), r'PULMONARY FIBROSIS|CYSTIC FIBROSIS|COPD|PULMONARY DISEASE|LUNG DISEASES, INTERSTITIAL') then 'Respiratory'
        when regexp_contains(upper({{ column }}), r'ARTHRITIS|LUPUS|ASTHMA|URTICARIA|SCLERODERMA|VASCULITIS|ARTERITIS|CROHN|COLITIS|PSORIASIS|LUPUS NEPHRITIS|FOOD HYPERSENSITIVITY|ALLERG') then 'Immunology'
        when regexp_contains(upper({{ column }}), r'HYPERTENSION|STROKE|MYOCARDIAL|HEART|CARDIOVASCULAR|THROMBOSIS|EMBOLISM') then 'Cardiovascular'
        when regexp_contains(upper({{ column }}), r'DIABETES|OBESITY|GROWTH|METABOLIC') then 'Metabolism & Endocrinology'
        else 'Other'
    end
{%- endmacro %}
