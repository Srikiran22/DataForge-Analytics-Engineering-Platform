{{
  config(
    materialized='view',
    schema='staging',
    tags=['staging']
  )
}}

with raw_returns as (
  select * from {{ source('raw', 'returns') }}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by return_id
      order by returned_at desc
    ) as rn
  from raw_returns
),

normalized as (
  select
    return_id,
    order_item_id,
    returned_at::timestamp as returned_at,
    trim(reason) as reason,
    quantity::bigint as quantity,
    returned_at::timestamp as updated_at,
    _source_name,
    _batch_id,
    _ingested_at,
    _source_file,
    _source_row_number
  from deduplicated
  where rn = 1
)

select * from normalized