{{
  config(
    materialized='view',
    schema='analytics',
    tags=['core'],
    contract={
      'enforced': true
    }
  )
}}

with snap as (
  select * from {{ ref('snap_customer') }}
),

final as (
  select
    {{ generate_surrogate_key(['customer_id', 'dbt_valid_from']) }} as customer_sk,
    customer_id,
    first_name,
    last_name,
    email,
    city,
    {{ generate_surrogate_key(['region_id']) }} as region_sk,
    segment,
    signup_date,
    dbt_valid_from,
    dbt_valid_to,
    case when dbt_valid_to is null then true else false end as is_current
  from snap
)

select * from final