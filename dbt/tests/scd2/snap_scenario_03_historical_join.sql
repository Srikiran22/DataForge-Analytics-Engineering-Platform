-- Scenario 3: fact-to-dimension SCD2 historical join correctness.
-- Every order must join to the dimension version valid AT order time, not just current.
-- Fails if any order's join produces 0 or >1 dimension matches.

with joined as (
  select o.order_id, count(*) as dim_matches
  from {{ ref('fct_orders') }} o
  join {{ ref('dim_customer') }} c
    on o.customer_sk = c.customer_sk
  group by o.order_id
)

select order_id, dim_matches
from joined
where dim_matches != 1