{{
  config(
    materialized='view',
    schema='staging',
    tags=['staging']
  )
}}

with raw_payments as (
  select * from {{ source('raw', 'payments') }}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by payment_id
      order by updated_at desc
    ) as rn
  from raw_payments
),

normalized as (
  select
    payment_id,
    order_id,
    amount_cents::bigint as amount_cents,
    trim(status) as status,
    trim(method) as method,
    event_ts::timestamp as event_ts,
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