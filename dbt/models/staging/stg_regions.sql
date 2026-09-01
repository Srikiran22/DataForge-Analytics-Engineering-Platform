{{
  config(
    materialized='view',
    schema='staging',
    tags=['staging']
  )
}}

with raw_regions as (
  select * from {{ source('raw', 'regions') }}
),

normalized as (
  select
    region_id,
    trim(region_name) as region_name,
    trim(country) as country,
    _source_name,
    _batch_id,
    _ingested_at,
    _source_file,
    _source_row_number
  from raw_regions
)

select * from normalized