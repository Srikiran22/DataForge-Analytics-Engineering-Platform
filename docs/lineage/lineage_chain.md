# Lineage Chain: orders.csv → mart_sales

Traced 2026-08-26 against live warehouse `data/warehouse/analytics.duckdb`.

## Full Chain

```
orders.csv                         (CSV, 724 daily files, 250,047 lines incl. replays)
  → ingestion/extractors/ndjson_file.py + pipeline.py (watermark, quarantine)
    → raw.orders (248,832 rows) + raw.quarantine_orders (1,738 rows: 523 malformed + 1,215 invalid FK)
    → raw.ingestion_watermarks (orders: 2026-08-25T23:54:35Z)
    + lineage.batch_lineage (orders/incremental 250,047 → 248,832)

  → dbt stg_orders (view, dedup ROW_NUMBER() keep max updated_at, normalize types)
    → 248,832 deduplicated rows, unique order_id

  → dbt snap_customer (snapshot analytics.snap_customer, SCD2, 40,003 versions)

  → dbt dim_customer (view on snap_customer, is_current + customer_sk)
  → dbt dim_date (1,461 days)

  → dbt fct_orders (incremental merge on order_id, lookback 7d, SCD2 join)
    → 215,026 rows (fact grain: one row per order)

  → dbt int_customer_orders (reusable view)

  → dbt mart_sales (table, contract enforced, gross/net revenue)
    → 215,026 rows

  → (future) Streamlit dashboard `mart_sales` panel — queries marts only, freshness via obs_pipeline_runs
```

## Verification

- `dbt docs generate` → `target/catalog.json` ( lineage graph for staging→intermediate→marts)
- Ingestion lineage: `SELECT source_name, rows_extracted, rows_loaded, rows_quarantined FROM lineage.batch_lineage WHERE source_name='orders'` → 250,047 / 248,832 / 1,738
- Column-level: `mart_sales.net_revenue` → `fct_orders.total_amount_cents` → `stg_orders.total_amount_cents` → `raw.orders.total_amount_cents` → `orders.csv`
- Upgrade path: at larger scale, OpenLineage + Marquez would emit events from ingestion + `dbt --store-failures`; currently dbt lineage + `lineage.batch_lineage` table cover same ground manually.

## Business → Mart Trace

All 5 marts trace to BQ IDs per `docs/business_questions.md` and `models/marts/schema.yml` descriptions.