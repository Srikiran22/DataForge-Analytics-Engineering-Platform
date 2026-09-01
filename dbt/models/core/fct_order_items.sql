{{
  config(
    materialized='incremental',
    schema='analytics',
    tags=['core'],
    unique_key='item_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns',
    contract={
      'enforced': true
    }
  )
}}

with stg as (
  select * from {{ ref('stg_order_items') }}
),

orders as (
  select order_sk, order_id
  from {{ ref('fct_orders') }}
),

products as (
  select product_sk, product_id
  from {{ ref('dim_product') }}
),

joined as (
  select
    {{ generate_surrogate_key(['i.item_id']) }} as order_item_sk,
    i.item_id,
    o.order_sk,
    p.product_sk,
    i.quantity,
    i.unit_price_cents,
    i.line_amount_cents,
    i.updated_at
  from {{ ref('stg_order_items') }} i
  join orders o on i.order_id = o.order_id
  join products p on i.product_id = p.product_id
)

select * from joined

{% if is_incremental() %}
  where updated_at > (select max(updated_at) from {{ this }})
    - interval '{{ var("lookback_days") }} days'
{% endif %}