-- Negative test: mart_sales must not contain cancelled or returned orders
-- (gross revenue should only include delivered/shipped)
select order_sk, status
from {{ ref('mart_sales') }}
where status in ('cancelled', 'returned', 'placed')