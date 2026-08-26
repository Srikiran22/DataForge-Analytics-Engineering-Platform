# Architecture Sketch — Phase 0 (text form; formal diagram maintained in `docs/architecture/`)

> Status: Phase 0 sketch. Regenerate whenever the implemented flow changes — diagram/code drift is a defect.

```
 SOURCE SYSTEMS                                   ORCHESTRATION: Airflow 3.3.x
 ──────────────                                   (single combined container,
  orders.csv            (CSV file)                 SQLite metadata, SequentialExecutor;
  order_events.json     (JSON file)                dev-grade by ADR-0002)
  products API          (FastAPI mock service)
  source_oltp (PG 17)   (OLTP relational source)      schedule: daily | catchup: documented
        │                                                     │
        ▼                                                     ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ INGESTION (Python pkg: extractors / loaders / watermark state)   │
 │  full + incremental loads · retry w/ backoff · idempotent batches│
 │  record-level dedup · quarantine of malformed records            │
 │  emits lineage rows (batch_id → raw table)                       │
 └──────────────────────────────────────────────────────────────────┘
        │  contract gate: parseable + batch_id assigned
        ▼
 ╔══════════════════════════════════════════════════════════════╗
 ║ RAW LAYER (DuckDB warehouse file; schema-on-read fidelity)   ║
 ║ raw.<source> tables + _batch_id/_ingested_at/_source_file    ║
 ║ raw.quarantine_<source> · raw.ingestion_watermarks           ║
 ╚══════════════════════════════════════════════════════════════╝
        │  GATE: structural contract satisfied? else FAIL pipeline
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STAGING (dbt): 1:1 rename/cast/normalize · UTC policy · no logic │
 └──────────────────────────────────────────────────────────────────┘
        │  GATE: dbt generic tests green (unique/not_null/
        │        relationships/accepted_values) or build halts
        ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ INTERMEDIATE (dbt): reusable business logic, DRY, metric defs    │
 │  int_customer_orders · int_payment_status · int_return_metrics … │
 └──────────────────────────────────────────────────────────────────┘
        ▼
 ╔══════════════════════════════════════════════════════════════╗
 ║ CORE STAR SCHEMA                                             ║
 ║ dims: dim_customer(SCD2 snapshot) · dim_product · dim_date · ║
 ║       dim_region                                             ║
 ║ facts: fct_orders(incr) · fct_order_items · fct_payments ·   ║
 ║        fct_returns                                           ║
 ║ contracts enforced on marts · snapshots feed SCD2 joins      ║
 ╚══════════════════════════════════════════════════════════════╝
        ▼
 ┌───────────────────────────┐   ┌────────────────────────────────┐
 │ MARTS (dbt)               │   │ OBSERVABILITY (operational)    │
 │ mart_sales                │   │ obs_pipeline_runs              │
 │ mart_customer_retention   │   │ obs_quality_checks             │
 │ mart_product_performance  │   │ obs_freshness                  │
 │ mart_inventory            │   │ (populated by pipeline itself) │
 │ mart_returns              │   └───────────────┬────────────────┘
 └─────────────┬─────────────┘                   │
               │ GATE: freshness SLA             │
               ▼                                 ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ STREAMLIT DASHBOARD (read-only DuckDB connection)                │
 │ revenue trend · retention · product perf · returns · inventory · │
 │ ★ data-freshness / pipeline-status panel (trust chain visible)   │
 └──────────────────────────────────────────────────────────────────┘

 CROSS-CUTTING
 ├── Quality layer: dbt tests + contracts + custom anomaly checks (ADR-0004)
 ├── Lineage: dbt docs graph + ingestion batch_lineage table (ADR-0005)
 ├── CI: ci-fast.yml (every PR) / ci-integration.yml (merge to main)
 └── Everything reproducible via docker compose + Make targets
```

## Inter-layer contracts (each arrow above = a defined precondition; formalized in `quality/contracts/` in Phase 6)

| Arrow | Precondition to cross |
|---|---|
| Source → Raw | Record parses; batch ID assigned. No business-validity requirement yet. |
| Raw → Staging | Structural schema contract holds (required columns/types). Violation ⇒ quarantine row or fail pipeline per §18 decision table. |
| Staging → Intermediate/Marts | dbt tests pass; failing test blocks downstream in `dbt build`. |
| Intermediate → Core | Contracts (`enforced: true`) compile-check column names/types on marts. |
| Marts → Dashboard | Freshness within SLA; staleness beyond threshold must be visibly flagged, never silently displayed as current. |

## Stack summary (all choices carry an ADR)

| Concern | Choice | ADR |
|---|---|---|
| Warehouse | DuckDB 1.5.x (file), Postgres 17 as OLTP source only | 0001 |
| Orchestrator | Airflow 3.3.x, combined container, dev-grade config | 0002 |
| Transformation | dbt-core ~1.12 + dbt-duckdb ~1.11 | 0003 |
| Data quality | dbt tests/contracts + custom checks, no GX | 0004 |
| Lineage | dbt docs graph + ingestion lineage table | 0005 |
| Dashboard | Streamlit, read-only, marts-only rule | 0006 |
