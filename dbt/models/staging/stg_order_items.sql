{{
  config(
    materialized='view',
    schema='staging',
    tags=['staging']
  )
}}

with raw_items as (
  select * from {{ source('raw', 'order_items') }}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by item_id
      order by updated_at desc
    ) as rn
  from raw_items
),

normalized as (
  select
    item_id,
    order_id,
    product_id,
    quantity::bigint as quantity,
    unit_price_cents::bigint as unit_price_cents,
    (quantity::bigint * unit_price_cents::bigint) as line_amount_cents,
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