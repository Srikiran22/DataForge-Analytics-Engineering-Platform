-- Scenario 1: snapshot produces versioned rows with valid SCD2 structure.
-- Fails only on structural breaks (e.g. is_current not boolean or valid_from null).

select customer_id
from {{ ref('snap_customer') }}
where dbt_valid_from is null
  or dbt_valid_to is not null and dbt_valid_to <= dbt_valid_from