with spine as (
    {{ dbt_utils.date_spine(datepart="day", start_date="cast('2019-01-01' as date)", end_date="cast('2031-01-01' as date)") }}
),

days as (
    select cast(date_day as date) as d from spine
)

select
    d as date_day,
    extract(year from d) as year,
    extract(quarter from d) as quarter_number,
    concat(cast(extract(year from d) as string), 'Q', cast(extract(quarter from d) as string)) as year_quarter,
    extract(month from d) as month_number,
    format_date('%b', d) as month_name,
    format_date('%Y-%m', d) as year_month,
    date_trunc(d, month) as month_start,
    extract(isoweek from d) as iso_week,
    format_date('%a', d) as weekday_name
from days
