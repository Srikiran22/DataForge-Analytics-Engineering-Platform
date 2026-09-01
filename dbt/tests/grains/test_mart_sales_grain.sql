-- Grain test: mart_sales must have one row per order_sk
select order_sk, count(*) as cnt
from {{ ref('mart_sales') }}
group by order_sk
having count(*) > 1