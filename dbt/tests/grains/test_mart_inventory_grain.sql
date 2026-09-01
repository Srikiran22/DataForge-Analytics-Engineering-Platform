-- Grain test: mart_inventory must have one row per (product_sk, warehouse_id)
select product_sk, warehouse_id, count(*) as cnt
from {{ ref('mart_inventory') }}
group by product_sk, warehouse_id
having count(*) > 1