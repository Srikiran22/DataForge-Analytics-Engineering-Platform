{{
  config(
    materialized='table',
    schema='analytics',
    tags=['core'],
    contract={
      'enforced': true
    }
  )
}}

with date_spine as (
  select (cast('2024-01-01' as date) + interval (n) day)::date as date_day
  from range(0, 1461) t(n)
),

final as (
  select
    (year(date_day) * 10000 + month(date_day) * 100 + day(date_day))::bigint as date_sk,
    date_day as date,
    year(date_day)::smallint as year,
    quarter(date_day)::smallint as quarter,
    month(date_day)::smallint as month,
    monthname(date_day) as month_name,
    day(date_day)::smallint as day,
    dayofweek(date_day)::smallint as day_of_week,
    dayname(date_day) as day_name,
    weekofyear(date_day)::smallint as week_of_year,
    (dayofweek(date_day) in (6,7)) as is_weekend,
    case
      when month(date_day) = 1 and day(date_day) = 1 then true
      when month(date_day) = 7 and day(date_day) = 4 then true
      when month(date_day) = 12 and day(date_day) = 25 then true
      when month(date_day) = 11 and dayofweek(date_day) = 4 and day(date_day) between 22 and 28 then true
      else false
    end as is_holiday,
    case
      when month(date_day) >= 10 then year(date_day) + 1
      else year(date_day)
    end as fiscal_year,
    case
      when month(date_day) in (10,11,12) then 1
      when month(date_day) in (1,2,3) then 2
      when month(date_day) in (4,5,6) then 3
      else 4
    end as fiscal_quarter
  from date_spine
)

select * from final