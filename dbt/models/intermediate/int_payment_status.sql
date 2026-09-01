{{
  config(
    materialized='view',
    schema='intermediate',
    tags=['intermediate']
  )
}}

with payments as (
  select
    p.payment_sk,
    p.payment_id,
    p.order_sk,
    p.amount_cents,
    p.status,
    p.method,
    p.event_ts,
    p.payment_date_sk,
    p.updated_at
  from {{ ref('fct_payments') }} p
),

order_payments as (
  select
    o.order_sk,
    o.order_id,
    sum(p.amount_cents) as total_paid_cents,
    sum(case when p.status = 'settled' then p.amount_cents else 0 end) as settled_cents,
    sum(case when p.status = 'refunded' then p.amount_cents else 0 end) as refunded_cents,
    max(case when p.status = 'settled' then p.event_ts end) as last_settled_at,
    bool_or(p.status = 'pending') as has_pending,
    bool_or(p.status = 'failed') as has_failed
  from {{ ref('fct_orders') }} o
  left join payments p on o.order_sk = p.order_sk
  group by o.order_sk, o.order_id
)

select * from order_payments