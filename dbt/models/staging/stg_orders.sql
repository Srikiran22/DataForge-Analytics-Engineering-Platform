{{
  config(
    materialized='view',
    schema='staging',
    tags=['staging']
  )
}}

with raw_orders as (
  select * from {{ source('raw', 'orders') }}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by order_id
      order by updated_at desc
    ) as rn
  from raw_orders
),

normalized as (
  select
    order_id,
    customer_id,
    order_ts::timestamp as order_ts,
    trim(status) as status,
    total_amount_cents::bigint as total_amount_cents,
    trim(currency) as currency,
    updated_at::timestamp as updated_at,
    _source_name,
    _batch_id,
    _ingested_at,
    _source_file,
    _source_row_number
  from deduplicated
  where rn = 1
)

select * from normalized