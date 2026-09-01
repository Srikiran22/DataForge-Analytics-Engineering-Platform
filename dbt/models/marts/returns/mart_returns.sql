{{
  config(
    materialized='table',
    schema='marts',
    tags=['marts', 'returns'],
    contract={
      'enforced': true
    }
  )
}}

with returns as (
  select
    r.return_sk,
    r.return_id,
    r.return_date_sk,
    r.reason,
    r.quantity,
    r.returned_at,
    p.product_sk,
    p.product_id,
    p.name as product_name,
    p.category,
    p.brand,
    oi.unit_price_cents,
    (r.quantity * oi.unit_price_cents) / 100.0 as returned_revenue,
    o.order_ts,
    c.customer_sk,
    c.region_sk,
    reg.region_name
  from {{ ref('fct_returns') }} r
  join {{ ref('fct_order_items') }} oi on r.order_item_sk = oi.order_item_sk
  join {{ ref('fct_orders') }} o on oi.order_sk = o.order_sk
  join {{ ref('dim_product') }} p on oi.product_sk = p.product_sk
  join {{ ref('dim_customer') }} c on o.customer_sk = c.customer_sk
  join {{ ref('dim_region') }} reg on c.region_sk = reg.region_sk
),

agg as (
  select
    reason,
    category,
    region_name,
    return_date_sk,
    sum(quantity) as total_returned_units,
    sum(returned_revenue) as total_returned_revenue,
    count(*) as return_count
  from returns
  group by reason, category, region_name, return_date_sk
)

select
  return_date_sk,
  d.date,
  reason,
  category,
  region_name,
  total_returned_units,
  total_returned_revenue,
  return_count
from agg
join {{ ref('dim_date') }} d on agg.return_date_sk = d.date_sk