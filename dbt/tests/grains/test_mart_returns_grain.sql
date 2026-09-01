-- Grain test: mart_returns must have one row per (return_date_sk, reason, category, region_name)
select return_date_sk, reason, category, region_name, count(*) as cnt
from {{ ref('mart_returns') }}
group by return_date_sk, reason, category, region_name
having count(*) > 1