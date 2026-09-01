{{
  config(
    materialized='incremental',
    schema='analytics',
    tags=['core'],
    unique_key='order_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns',
    contract={
      'enforced': true
    }
  )
}}

with stg as (
  select * from {{ ref('stg_orders') }}
),

customers as (
  select customer_sk, customer_id, dbt_valid_from, dbt_valid_to
  from {{ ref('dim_customer') }}
),

date_dim as (
  select date_sk, date
  from {{ ref('dim_date') }}
),

joined as (
  select
    {{ generate_surrogate_key(['o.order_id']) }} as order_sk,
    o.order_id,
    c.customer_sk,
    d.date_sk as order_date_sk,
    o.status,
    o.total_amount_cents,
    o.currency,
    o.order_ts,
    o.updated_at
  from {{ ref('stg_orders') }} o
  join customers c
    on o.customer_id = c.customer_id
    and o.order_ts >= c.dbt_valid_from
    and (c.dbt_valid_to is null or o.order_ts < c.dbt_valid_to)
  join date_dim d
    on cast(o.order_ts as date) = d.date
)

select * from joined

{% if is_incremental() %}
  where updated_at > (select max(updated_at) from {{ this }})
    - interval '{{ var("lookback_days") }} days'
{% endif %}