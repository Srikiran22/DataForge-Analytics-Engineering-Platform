-- Negative test: No order_ts in the future (relative to max date in data)
select order_sk, order_ts
from {{ ref('fct_orders') }}
where order_ts > (select max(order_ts) from {{ ref('fct_orders') }})