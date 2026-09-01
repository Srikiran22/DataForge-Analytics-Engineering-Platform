{{
  config(
    materialized='table',
    schema='marts',
    tags=['marts', 'product_performance'],
    contract={
      'enforced': true
    }
  )
}}

with sales as (
  select
    p.product_sk,
    p.product_id,
    p.name,
    p.category,
    p.brand,
    sum(oi.quantity) as units_sold,
    sum(oi.line_amount_cents) / 100.0 as product_revenue,
    count(distinct oi.order_sk) as order_count,
    avg(oi.unit_price_cents) / 100.0 as avg_unit_price
  from {{ ref('dim_product') }} p
  join {{ ref('fct_order_items') }} oi on p.product_sk = oi.product_sk
  join {{ ref('fct_orders') }} o on oi.order_sk = o.order_sk
  where o.status in ('delivered', 'shipped')
  group by p.product_sk, p.product_id, p.name, p.category, p.brand
),

returns as (
  select
    p.product_sk,
    sum(r.quantity) as returned_units,
    sum(r.quantity * oi.unit_price_cents) / 100.0 as returned_revenue
  from {{ ref('fct_returns') }} r
  join {{ ref('fct_order_items') }} oi on r.order_item_sk = oi.order_item_sk
  join {{ ref('dim_product') }} p on oi.product_sk = p.product_sk
  group by p.product_sk
),

final as (
  select
    s.product_sk,
    s.product_id,
    s.name,
    s.category,
    s.brand,
    s.units_sold,
    s.product_revenue,
    s.order_count,
    s.avg_unit_price,
    coalesce(r.returned_units, 0) as returned_units,
    coalesce(r.returned_revenue, 0) as returned_revenue,
    case
      when s.units_sold > 0 then coalesce(r.returned_units, 0)::float / s.units_sold
      else 0
    end as return_rate,
    rank() over (order by s.product_revenue desc) as revenue_rank
  from sales s
  left join returns r on s.product_sk = r.product_sk
)

select * from final