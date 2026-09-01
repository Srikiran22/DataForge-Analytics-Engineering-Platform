-- Scenario 2: no duplicate hash for same customer+valid_from (multi-attr change must be one version).

with ranked as (
  select customer_id, dbt_valid_from, dbt_scd_id, count(*) over (partition by customer_id, dbt_valid_from) as cnt
  from {{ ref('snap_customer') }}
)

select customer_id, dbt_valid_from, cnt
from ranked
where cnt > 1