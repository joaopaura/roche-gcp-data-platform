{#
  MedDRA preferred terms that describe product use, medication errors, lack of effect, the treated
  disease or non-specific outcomes rather than an adverse reaction. Standard practice is to exclude
  them from disproportionality screening (they create "signals" that are not clinical findings).
#}
{% macro is_non_clinical_term(column) -%}
    regexp_contains(lower({{ column }}),
        r'^(off label use|no adverse event|drug ineffective|death|disease progression|condition aggravated'
        || r'|malignant neoplasm progression|therapeutic response decreased|therapeutic product effect (decreased|incomplete)'
        || r'|drug effect (decreased|incomplete)|treatment noncompliance|therapy interrupted|therapy cessation'
        || r'|therapy non-responder|therapy partial responder|drug interaction|underdose|overdose|contraindicated product administered'
        || r'|inappropriate schedule of product administration|incorrect dose administered|incorrect route of product administration'
        || r'|wrong technique in product usage process|drug dose omission|drug dose omission by device|expired product administered'
        || r'|exposure during pregnancy|maternal exposure during pregnancy|intentional product misuse|intentional product use issue)$'
        || r'|product |device|medication error|off label|circumstance or information')
{%- endmacro %}
