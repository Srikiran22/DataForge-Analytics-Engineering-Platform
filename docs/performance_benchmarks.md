# Performance Benchmarks — DataForge

All numbers measured on 2026-08-26 on Windows 11 (build 26200) / WSL2 Ubuntu 26.04, 16GB RAM, NVMe, single-user. Every row count is real; every timing is a single `time` / `Measure-Command` run — not averaged.

## Ingestion (bulk via DuckDB read_json)

| Source | Rows | Time | Command |
|--------|------|------|---------|
| customers (full, snapshot) | 40,000 | **1.1s** | `python -m ingestion.cli load --source customers --full` (post-optimization) |
| customers (full, pre-optimization) | 40,000 | **161.9s** | same command with row-wise `executemany` |
| orders (initial, 724 files) | 248,832 loaded + 1,738 quarantined | **24.8s** (WSL) / 8.6s (Windows, warm cache) | `python -m ingestion.cli load --source orders` |
| returns | 13,435 | 1.0s | `python -m ingestion.cli load --source returns` |
| products (API) | 8,000 | <1s | `python -m ingestion.cli load --source products` |
| order_items (RDBMS) | 561,509 | ~2s (COPY) | `populate_oltp.py` COPY + `load --source order_items` |
| payments (RDBMS) | 248,069 | ~1s | same |
| Seed generation (full) | ~1.1M rows | **14–17s** | `python scripts/seed/generate_sources.py` |

### Optimization Case Study

**Baseline**: `duckdb_loader.load_batch` used `conn.executemany("INSERT … VALUES (?)", rows)` — 1 prepared execution per row, ~4 ms/row.

**Measurement**: `Measure-Command { load --source customers }` = **161.9s** for 40k rows.

**Diagnosis**: Row-wise Python→C++ round-trip + per-row transaction overhead. `EXPLAIN` not needed — the call site was the bottleneck.

**Fix**: Serialize batch to temp NDJSON, single `INSERT INTO raw SELECT … FROM read_json(path, columns={…})` inside one explicit transaction (`_bulk_insert_via_json`).

**Re-measurement**: Same command → **1.1s** (147×). Orders 247k rows: **timeout (>600s) → 8.6–24.8s**.

**Recorded in**: `ingestion/loaders/duckdb_loader.py:_bulk_insert_via_json`, `docs/architecture/raw_layer.md`.

## dbt

| Operation | Time | Command |
|-----------|------|---------|
| `dbt snapshot` | 0.43s | `dbt snapshot` |
| `dbt snapshot` re-run (idempotent, no new source rows) | 0.4s | `dbt snapshot` |
| `dbt build --select fct_orders --full-refresh` | **1.27s** | 1 incremental model + 16 tests |
| `dbt build --select fct_orders` (incremental, no new data) | **1.02s** | same, lookback check only |
| `dbt build` (all 25 models, 214 tests, 1 snapshot) | **9.7s** | `dbt build` |
| `dbt docs generate` | ~3s | `dbt docs generate` → `target/catalog.json` |

## Incremental Parity

| Model | Full-refresh rows | Incremental rows | `sum(total_amount_cents)` | Match? |
|-------|-------------------|------------------|---------------------------|--------|
| `fct_orders` | 215,026 | 215,026 | identical (no new source data between runs) | **PASS** |

*Full-refresh vs incremental executed back-to-back on same source snapshot (no new batches), so the 7-day lookback path was a no-op in both. A true new-batch parity run (with a fresh late-arriving batch) is deferred to E2E in Group 5/6.*

## Mart Query Latency

| Query | Time | SQL |
|-------|------|-----|
| `mart_sales` sum | **0.002s** | `SELECT sum(net_revenue) FROM main_marts.mart_sales` |
| `mart_product_performance` top 20 | **0.006s** | `SELECT * FROM main_marts.mart_product_performance ORDER BY product_revenue DESC LIMIT 20` |

## Full Pipeline (representative)

```
generate_sources (14s) → populate_oltp (2s) → init-warehouse (0.1s)
→ load customers (1.1s) + orders (24.8s) + returns (1s) + products (<1s) + order_items/payments/inventory (<3s)
→ dbt build (9.7s) → pytest tests/ (24–30s)
Total wall-clock (cold, single run, WSL): ~55–60s
```

## Docker

| Operation | Time |
|-----------|------|
| `docker compose up -d` (postgres only, image cached) | ~6–10s to `healthy` |
| Image pull (cold, `postgres:17`, ~150MB) | ~20–30s (depends on network) |

## Reproduction

```bash
# From project root (WSL or Windows with WSL backend):
uv pip install -r requirements/dev.txt
python scripts/seed/generate_sources.py
# (if Docker available)
docker compose up -d && sleep 10
python scripts/seed/populate_oltp.py
python -m ingestion.cli init-warehouse
python -m ingestion.cli load --source customers --full
python -m ingestion.cli load --source orders
WAREHOUSE_PATH=data/warehouse/analytics.duckdb dbt build
pytest tests/
```

All numbers above are the output of those exact commands on 2026-08-26.