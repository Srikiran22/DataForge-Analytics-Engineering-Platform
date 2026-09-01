{{
  config(
    materialized='view',
    schema='intermediate',
    tags=['intermediate']
  )
}}

with returns as (
  select
    r.return_sk,
    r.return_id,
    r.order_item_sk,
    r.return_date_sk,
    r.reason,
    r.quantity,
    r.returned_at
  from {{ ref('fct_returns') }} r
),

order_item_returns as (
  select
    oi.order_item_sk,
    oi.order_sk,
    oi.product_sk,
    oi.quantity as ordered_quantity,
    oi.unit_price_cents,
    oi.line_amount_cents,
    sum(r.quantity) as returned_quantity,
    sum(r.quantity * oi.unit_price_cents) as returned_amount_cents,
    max(r.returned_at) as last_returned_at,
    string_agg(distinct r.reason, ', ') as return_reasons
  from {{ ref('fct_order_items') }} oi
  left join returns r on oi.order_item_sk = r.order_item_sk
  group by oi.order_item_sk, oi.order_sk, oi.product_sk, oi.quantity, oi.unit_price_cents, oi.line_amount_cents
)

select * from order_item_returns