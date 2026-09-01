-- Grain test: mart_product_performance must have one row per product_sk
select product_sk, count(*) as cnt
from {{ ref('mart_product_performance') }}
group by product_sk
having count(*) > 1