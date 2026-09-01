{{
  config(
    materialized='table',
    schema='analytics',
    tags=['core'],
    contract={
      'enforced': true
    }
  )
}}

with stg as (
  select * from {{ ref('stg_products') }}
),

final as (
  select
    {{ generate_surrogate_key(['product_id']) }} as product_sk,
    product_id,
    name,
    category,
    price_cents,
    active,
    brand
  from stg
)

select * from final