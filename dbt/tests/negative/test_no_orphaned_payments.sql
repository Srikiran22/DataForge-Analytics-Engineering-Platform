-- Negative test: fct_payments must not have orphaned payments (no matching order)
select p.payment_sk
from {{ ref('fct_payments') }} p
left join {{ ref('fct_orders') }} o on p.order_sk = o.order_sk
where o.order_sk is null