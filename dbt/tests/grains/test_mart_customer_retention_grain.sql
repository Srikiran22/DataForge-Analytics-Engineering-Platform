-- Grain test: mart_customer_retention must have one row per (cohort_month, order_month)
select cohort_month, order_month, count(*) as cnt
from {{ ref('mart_customer_retention') }}
group by cohort_month, order_month
having count(*) > 1