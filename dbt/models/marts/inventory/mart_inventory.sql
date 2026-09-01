{{
  config(
    materialized='table',
    schema='marts',
    tags=['marts', 'inventory'],
    contract={
      'enforced': true
    }
  )
}}

with inventory as (
  select
    il.product_id,
    il.warehouse_id,
    il.stock_on_hand,
    il.reorder_point,
    il.updated_at,
    p.product_sk,
    p.product_id,
    p.name,
    p.category,
    p.brand
  from {{ ref('stg_inventory_levels') }} il
  join {{ ref('dim_product') }} p on il.product_id = p.product_id
),

sales_velocity as (
  select
    oi.product_sk,
    sum(oi.quantity) / 30.0 as avg_daily_units_sold  -- last 30 days
  from {{ ref('fct_order_items') }} oi
  join {{ ref('fct_orders') }} o on oi.order_sk = o.order_sk
  where o.status in ('delivered', 'shipped')
    and o.order_ts >= (select max(order_ts) from {{ ref('fct_orders') }} where status in ('delivered', 'shipped')) - interval '30 days'
  group by oi.product_sk
),

final as (
  select
    i.product_sk,
    i.product_id,
    i.name,
    i.category,
    i.brand,
    i.warehouse_id,
    i.stock_on_hand,
    i.reorder_point,
    i.updated_at as snapshot_date,
    coalesce(sv.avg_daily_units_sold, 0) as avg_daily_units_sold,
    case
      when coalesce(sv.avg_daily_units_sold, 0) > 0
      then floor(i.stock_on_hand / coalesce(sv.avg_daily_units_sold, 0))
      else null
    end as days_of_cover,
    case
      when i.stock_on_hand <= i.reorder_point then true
      else false
    end as low_stock_flag
  from inventory i
  left join sales_velocity sv on i.product_sk = sv.product_sk
)

select * from final