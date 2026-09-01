{{
  config(
    materialized='table',
    schema='analytics',
    tags=['core'],
    contract={
      'enforced': true
    }
  )
}}

with stg as (
  select * from {{ ref('stg_regions') }}
),

final as (
  select
    {{ generate_surrogate_key(['region_id']) }} as region_sk,
    region_id,
    region_name,
    country
  from stg
)

select * from final