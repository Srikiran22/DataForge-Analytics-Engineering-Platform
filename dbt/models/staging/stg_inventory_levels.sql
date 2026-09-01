{{
  config(
    materialized='view',
    schema='staging',
    tags=['staging']
  )
}}

with raw_inv as (
  select * from {{ source('raw', 'inventory_levels') }}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by product_id, warehouse_id
      order by updated_at desc
    ) as rn
  from raw_inv
),

normalized as (
  select
    product_id,
    warehouse_id,
    stock_on_hand::bigint as stock_on_hand,
    reorder_point::bigint as reorder_point,
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