{{
  config(
    materialized='view',
    schema='staging',
    tags=['staging']
  )
}}

with raw_customers as (
  select * from {{ source('raw', 'customers') }}
),

normalized as (
  select
    customer_id,
    trim(first_name) as first_name,
    trim(last_name) as last_name,
    case
      when trim(email) = '' then null
      else lower(trim(email))
    end as email,
    trim(city) as city,
    trim(region_id) as region_id,
    trim(segment) as segment,
    signup_date::date as signup_date,
    updated_at::timestamp as updated_at,
    _source_name,
    _batch_id,
    _ingested_at,
    _source_file,
    _source_row_number
  from raw_customers
)

select * from normalized