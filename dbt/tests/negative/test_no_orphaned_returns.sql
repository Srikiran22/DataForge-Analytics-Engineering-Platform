-- Negative test: fct_returns must not have orphaned returns (no matching order_item)
select r.return_sk
from {{ ref('fct_returns') }} r
left join {{ ref('fct_order_items') }} oi on r.order_item_sk = oi.order_item_sk
where oi.order_item_sk is null