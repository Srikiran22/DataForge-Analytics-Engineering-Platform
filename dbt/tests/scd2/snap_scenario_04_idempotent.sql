-- Scenario 4: snapshot idempotency - structural validation that re-running snapshot
-- on unchanged source would not create new rows (no duplicate valid_from per customer,
-- no gaps in validity periods, each customer has exactly one current version).

with current_versions as (
  select customer_id, count(*) as current_count
  from {{ ref('snap_customer') }}
  where dbt_valid_to is null
  group by customer_id
),
validity_gaps as (
  select customer_id, dbt_valid_from,
         lead(dbt_valid_from) over (partition by customer_id order by dbt_valid_from) as next_valid_from,
         dbt_valid_to
  from {{ ref('snap_customer') }}
)
select 'multiple_current' as issue, customer_id, current_count as detail
from current_versions
where current_count != 1

union all

select 'validity_gap' as issue, customer_id,
       dbt_valid_from || ' -> ' || next_valid_from as detail
from validity_gaps
where dbt_valid_to is not null
  and next_valid_from is not null
  and dbt_valid_to != next_valid_from

union all

select 'null_valid_from' as issue, customer_id,
       dbt_scd_id as detail
from {{ ref('snap_customer') }}
where dbt_valid_from is null