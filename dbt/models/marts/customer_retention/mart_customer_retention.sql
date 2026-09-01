{{
  config(
    materialized='table',
    schema='marts',
    tags=['marts', 'customer_retention'],
    contract={
      'enforced': true
    }
  )
}}

with customer_first_order as (
  select
    c.customer_sk,
    c.customer_id,
    c.segment,
    c.signup_date,
    min(o.order_ts) as first_order_ts,
    date_trunc('month', min(o.order_ts))::date as cohort_month
  from {{ ref('dim_customer') }} c
  join {{ ref('fct_orders') }} o on c.customer_sk = o.customer_sk
  where o.status in ('delivered', 'shipped')
  group by c.customer_sk, c.customer_id, c.segment, c.signup_date
),

customer_orders as (
  select
    cfo.customer_sk,
    cfo.cohort_month,
    o.order_ts,
    o.total_amount_cents,
    date_trunc('month', o.order_ts)::date as order_month
  from customer_first_order cfo
  join {{ ref('fct_orders') }} o on cfo.customer_sk = o.customer_sk
  where o.status in ('delivered', 'shipped')
),

cohort_agg as (
  select
    cohort_month,
    order_month,
    count(distinct customer_sk) as customers,
    sum(total_amount_cents) / 100.0 as cohort_revenue,
    count(distinct customer_sk)::float / max(customers) over (partition by cohort_month) as retention_rate
  from customer_orders
  group by cohort_month, order_month
),

repeat_purchase as (
  select
    cfo.cohort_month,
    sum(rp.order_count) as total_repeat_orders,
    min(rp.first_order) as cohort_first_repeat_order,
    max(rp.last_order) as cohort_last_repeat_order
  from customer_first_order cfo
  join (
    select
      customer_sk,
      count(*) as order_count,
      min(order_ts) as first_order,
      max(order_ts) as last_order
    from {{ ref('fct_orders') }}
    where status in ('delivered', 'shipped')
    group by customer_sk
    having count(*) > 1
  ) rp on cfo.customer_sk = rp.customer_sk
  group by cfo.cohort_month
)

select
  ca.cohort_month,
  ca.order_month,
  ca.customers,
  ca.cohort_revenue,
  ca.retention_rate,
  coalesce(rp.total_repeat_orders, 0)::bigint as repeat_orders,
  rp.cohort_first_repeat_order as first_order,
  rp.cohort_last_repeat_order as last_order
from cohort_agg ca
left join repeat_purchase rp on ca.cohort_month = rp.cohort_month