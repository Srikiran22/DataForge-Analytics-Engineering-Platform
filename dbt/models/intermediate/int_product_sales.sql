{{
  config(
    materialized='view',
    schema='intermediate',
    tags=['intermediate']
  )
}}

with product_sales as (
  select
    p.product_sk,
    p.product_id,
    p.name as product_name,
    p.category,
    p.brand,
    p.price_cents,
    oi.order_item_sk,
    oi.order_sk,
    oi.quantity,
    oi.unit_price_cents,
    oi.line_amount_cents,
    o.order_ts,
    o.order_date_sk,
    o.customer_sk
  from {{ ref('dim_product') }} p
  join {{ ref('fct_order_items') }} oi on p.product_sk = oi.product_sk
  join {{ ref('fct_orders') }} o on oi.order_sk = o.order_sk
)

select * from product_sales