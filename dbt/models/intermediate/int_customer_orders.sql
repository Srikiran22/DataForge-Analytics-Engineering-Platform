{{
  config(
    materialized='view',
    schema='intermediate',
    tags=['intermediate']
  )
}}

with customer_orders as (
  select
    c.customer_sk,
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.city,
    c.region_sk,
    c.segment,
    c.signup_date,
    o.order_sk,
    o.order_id,
    o.order_ts,
    o.order_date_sk,
    o.status,
    o.total_amount_cents,
    o.currency,
    o.updated_at as order_updated_at
  from {{ ref('dim_customer') }} c
  join {{ ref('fct_orders') }} o on c.customer_sk = o.customer_sk
)

select * from customer_orders