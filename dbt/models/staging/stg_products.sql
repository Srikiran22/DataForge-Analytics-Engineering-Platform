{{
  config(
    materialized='view',
    schema='staging',
    tags=['staging']
  )
}}

with raw_products as (
  select * from {{ source('raw', 'products') }}
),

normalized as (
  select
    product_id,
    trim(name) as name,
    lower(trim(category)) as category,
    price_cents::bigint as price_cents,
    case
      when lower(trim(active)) in ('true', '1', 'yes') then true
      else false
    end as active,
    case
      when trim(brand) = '' then null
      else trim(brand)
    end as brand,
    _source_name,
    _batch_id,
    _ingested_at,
    _source_file,
    _source_row_number
  from raw_products
)

select * from normalized