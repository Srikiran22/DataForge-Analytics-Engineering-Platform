-- Negative test: fct_order_items must not have orphaned items (no matching order)
select oi.order_item_sk
from {{ ref('fct_order_items') }} oi
left join {{ ref('fct_orders') }} o on oi.order_sk = o.order_sk
where o.order_sk is null