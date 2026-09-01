{% snapshot snap_customer %}

{{
  config(
    target_schema='analytics',
    unique_key='customer_id',
    strategy='timestamp',
    updated_at='updated_at',
    invalidate_hard_deletes=true,
    tags=['scd2']
  )
}}

select
  customer_id,
  first_name,
  last_name,
  email,
  city,
  region_id,
  segment,
  signup_date,
  updated_at
from {{ ref('stg_customers') }}

{% endsnapshot %}