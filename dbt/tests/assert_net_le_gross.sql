-- Net revenue must never exceed gross revenue (otherwise discount/return logic is broken).

select order_sk
from {{ ref('mart_sales') }}
where net_revenue > gross_revenue