{{
  config(
    materialized='incremental',
    schema='analytics',
    tags=['core'],
    unique_key='return_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns',
    contract={
      'enforced': true
    }
  )
}}

with stg as (
  select * from {{ ref('stg_returns') }}
),

order_items as (
  select order_item_sk, item_id
  from {{ ref('fct_order_items') }}
),

date_dim as (
  select date_sk, date
  from {{ ref('dim_date') }}
),

joined as (
  select
    {{ generate_surrogate_key(['r.return_id']) }} as return_sk,
    r.return_id,
    oi.order_item_sk,
    d.date_sk as return_date_sk,
    r.reason,
    r.quantity,
    r.returned_at,
    r.updated_at
  from {{ ref('stg_returns') }} r
  join order_items oi on r.order_item_id = oi.item_id
  join date_dim d on cast(r.returned_at as date) = d.date
)

select * from joined

{% if is_incremental() %}
  where updated_at > (select max(updated_at) from {{ this }})
    - interval '{{ var("lookback_days") }} days'
{% endif %}