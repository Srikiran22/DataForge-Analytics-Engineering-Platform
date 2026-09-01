{{
  config(
    materialized='view',
    schema='observability',
    tags=['observability']
  )
}}

-- Operational observability from real pipeline state (no heavyweight stack).
-- Business layer (marts) remains separate — this view exposes _source freshness,
-- row counts per batch, and quarantine counts as seen in the warehouse now.

with row_counts as (
  select 'customers' as source_name, count(*) as row_count, max(_ingested_at) as last_ingested_at from {{ source('raw', 'customers') }}
  union all select 'orders', count(*), max(_ingested_at) from {{ source('raw', 'orders') }}
  union all select 'order_items', count(*), max(_ingested_at) from {{ source('raw', 'order_items') }}
  union all select 'payments', count(*), max(_ingested_at) from {{ source('raw', 'payments') }}
  union all select 'returns', count(*), max(_ingested_at) from {{ source('raw', 'returns') }}
  union all select 'products', count(*), max(_ingested_at) from {{ source('raw', 'products') }}
),

watermarks as (
  -- ingestion_watermarks lives in schema raw; read via direct relation
  select * from raw.ingestion_watermarks
),

quarantine as (
  select 'orders' as source_name, count(*) as quarantined from raw.quarantine_orders
  union all select 'returns', count(*) from raw.quarantine_returns
)

select
  rc.source_name,
  rc.row_count,
  rc.last_ingested_at,
  w.watermark_value as last_watermark,
  coalesce(q.quarantined, 0) as quarantined_rows
from row_counts rc
left join watermarks w on rc.source_name = w.source_name
left join quarantine q on rc.source_name = q.source_name