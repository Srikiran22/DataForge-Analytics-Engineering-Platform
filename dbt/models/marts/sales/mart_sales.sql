{{
  config(
    materialized='table',
    schema='marts',
    tags=['marts', 'sales'],
    contract={
      'enforced': true
    }
  )
}}

with orders as (
  select
    o.order_sk,
    o.order_id,
    o.customer_sk,
    o.order_date_sk,
    o.status,
    o.total_amount_cents,
    o.currency,
    o.order_ts,
    d.date,
    d.year,
    d.month,
    d.quarter,
    d.month_name,
    c.region_sk,
    r.region_name,
    r.country
  from {{ ref('fct_orders') }} o
  join {{ ref('dim_date') }} d on o.order_date_sk = d.date_sk
  join {{ ref('dim_customer') }} c on o.customer_sk = c.customer_sk
  join {{ ref('dim_region') }} r on c.region_sk = r.region_sk
  where o.status in ('delivered', 'shipped')
),

payments as (
  select
    order_sk,
    sum(case when status = 'settled' then amount_cents else 0 end) as settled_cents,
    sum(case when status = 'refunded' then amount_cents else 0 end) as refunded_cents
  from {{ ref('fct_payments') }}
  group by order_sk
),

returns as (
  select
    o.order_sk,
    sum(r.quantity * oi.unit_price_cents) as returned_amount_cents
  from {{ ref('fct_returns') }} r
  join {{ ref('fct_order_items') }} oi on r.order_item_sk = oi.order_item_sk
  join {{ ref('fct_orders') }} o on oi.order_sk = o.order_sk
  group by o.order_sk
),

final as (
  select
    o.order_sk,
    o.order_id,
    o.date,
    o.year,
    o.month,
    o.quarter,
    o.month_name,
    o.region_name,
    o.country,
    o.status,
    o.total_amount_cents,
    o.currency,
    o.total_amount_cents / 100.0 as gross_revenue,
    coalesce(p.settled_cents, 0) / 100.0 as settled_revenue,
    coalesce(r.returned_amount_cents, 0) / 100.0 as returned_revenue,
    (o.total_amount_cents - coalesce(r.returned_amount_cents, 0)) / 100.0 as net_revenue
  from orders o
  left join payments p on o.order_sk = p.order_sk
  left join returns r on o.order_sk = r.order_sk
)

select * from final