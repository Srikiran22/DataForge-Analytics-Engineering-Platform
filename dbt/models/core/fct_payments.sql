{{
  config(
    materialized='incremental',
    schema='analytics',
    tags=['core'],
    unique_key='payment_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns',
    contract={
      'enforced': true
    }
  )
}}

with stg as (
  select * from {{ ref('stg_payments') }}
),

orders as (
  select order_sk, order_id
  from {{ ref('fct_orders') }}
),

date_dim as (
  select date_sk, date
  from {{ ref('dim_date') }}
),

joined as (
  select
    {{ generate_surrogate_key(['p.payment_id']) }} as payment_sk,
    p.payment_id,
    o.order_sk,
    d.date_sk as payment_date_sk,
    p.amount_cents,
    p.status,
    p.method,
    p.event_ts,
    p.updated_at
  from {{ ref('stg_payments') }} p
  join orders o on p.order_id = o.order_id
  join date_dim d on cast(p.event_ts as date) = d.date
)

select * from joined

{% if is_incremental() %}
  where updated_at > (select max(updated_at) from {{ this }})
    - interval '{{ var("lookback_days") }} days'
{% endif %}