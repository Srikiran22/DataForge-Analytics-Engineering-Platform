# DataForge

DataForge is a local-first analytics engineering project that builds a reproducible batch ELT pipeline from source systems to analytics-ready marts and a read-only dashboard.

The main goal is to make the data path explicit and testable:

```
CSV / NDJSON / REST API / PostgreSQL
                |
                v
        Python ingestion
                |
                v
          Raw DuckDB
                |
                v
              dbt
   staging -> intermediate
             -> core -> marts
                |
                v
        Streamlit dashboard
```

The repository also includes an Apache Airflow DAG that orchestrates the same pipeline for scheduled execution.

## What is included

### Ingestion

The Python ingestion package supports eight sources across four source types:

| Source | Type | Load mode |
|---|---|---|
| Customers | CSV | Full |
| Regions | CSV | Full |
| Orders | NDJSON | Incremental |
| Returns | NDJSON | Incremental |
| Products | REST API | Snapshot |
| Order items | PostgreSQL | Incremental |
| Payments | PostgreSQL | Incremental |
| Inventory levels | PostgreSQL | Incremental |

Incremental sources use watermarks. Each run receives a batch ID, and rerunning the same batch ID replaces the rows from that batch instead of appending a second copy.

### Raw layer

Raw data is stored in DuckDB with the original payload represented as strings plus ingestion metadata such as:

- `_source_name`
- `_batch_id`
- `_ingested_at`
- `_source_file`
- `_source_row_number`

Malformed records and invalid customer references are quarantined where a quarantine table is configured.

Duplicates are detected for observability, but the raw layer intentionally preserves them. Deduplication is handled downstream rather than changing the source representation.

### dbt models

The dbt project is split into four transformation layers:

```
staging
  -> intermediate
  -> core
  -> marts
```

- **Staging:** source cleanup, casting, and normalization
- **Intermediate:** reusable business transformations
- **Core:** analytical dimensions and fact tables
- **Marts:** business-facing tables with enforced dbt contracts

The core layer includes an SCD2 customer dimension and incremental fact processing. The mart layer currently covers sales, customer retention, product performance, returns, and inventory.

### Dashboard

The Streamlit dashboard is intentionally a consumer of marts rather than a second transformation layer.

It exposes:

- Sales and revenue trends
- Average order value and order counts
- Customer retention and cohort data
- Product performance
- Returns
- Inventory and low-stock status
- Pipeline freshness and operational status

The dashboard contains a runtime query guard that rejects accidental reads from raw, staging, fact, dimension, intermediate, and information-schema relations.

### Airflow

`airflow/dags/dataforge_daily.py` defines the scheduled pipeline:

```
extract/load sources
        -> raw validation
        -> dbt snapshot
        -> staging
        -> intermediate
        -> core
        -> marts
        -> quality checks
        -> publish
```

The DAG has eight source tasks, retries with exponential backoff, a 20-minute execution timeout, and `max_active_runs=1`.

The DAG is tested for parsing and dependency structure. An Airflow scheduler/webserver deployment is not included in the repository.

## Project structure

```
DataForge/
├── ingestion/             # Extraction, watermarks, quarantine, loading
├── dbt/                   # dbt project, models, tests, macros, snapshots
├── airflow/               # Airflow DAG and DAG tests
├── dashboards/            # Streamlit dashboard
├── services/              # Local mock Products API
├── scripts/               # Seed data and supporting utilities
├── configs/               # Deterministic seed configuration
├── quality/               # Supporting quality configuration
├── tests/                 # Unit, integration, and dashboard tests
├── docs/                  # Architecture, ADRs, metrics, quality, security
├── requirements/          # Runtime and development dependencies
├── docker-compose.yml     # PostgreSQL source database
├── .env.example           # Local environment template
└── Makefile               # Common development commands
```

## Requirements

For the core Python tooling:

- Python 3.13
- Docker for the PostgreSQL source
- `uv` or pip

The repository's `requirements/dev.txt` installs the Python ingestion and test dependencies. dbt, the dashboard dependencies, and Airflow are installed separately because they are not part of that file.

The CI workflow installs:

- `requirements/dev.txt`
- `dashboards/requirements.txt`
- `dbt-duckdb`

Airflow dependencies are required only when running the DAG locally.

## Getting started

### 1. Create the development environment

Using the Makefile:

```bash
make venv
```

Or install the development requirements directly:

```bash
uv venv .venv --python 3.13
uv pip install -r requirements/dev.txt --python .venv/Scripts/python.exe
```

### 2. Configure local environment values

Copy `.env.example` to `.env` and adjust the PostgreSQL and local path settings as needed.

The checked-in configuration uses PostgreSQL on port `5433` and the DuckDB warehouse at:

```
data/warehouse/analytics.duckdb
```

### 3. Generate the source data

```bash
python scripts/seed/generate_sources.py
```

The generator uses the seed and volumes in `configs/seed.yaml`. Changing those values changes the generated dataset and invalidates the documented benchmark numbers.

### 4. Start PostgreSQL

```bash
docker compose up -d
```

Then populate the OLTP source:

```bash
python scripts/seed/populate_oltp.py
```

### 5. Start the Products API

The mock Products API is a separate local FastAPI process; it is not started by `docker compose`.

```bash
uvicorn services.products_api.main:app --port 8100
```

The default ingestion configuration expects:

```
http://localhost:8100
```

### 6. Initialize the warehouse and load sources

```bash
python -m ingestion.cli init-warehouse

python -m ingestion.cli load --source customers --full
python -m ingestion.cli load --source regions
python -m ingestion.cli load --source orders
python -m ingestion.cli load --source returns
python -m ingestion.cli load --source products
python -m ingestion.cli load --source order_items
python -m ingestion.cli load --source payments
python -m ingestion.cli load --source inventory_levels
```

### 7. Build the dbt project

From the repository root:

```bash
WAREHOUSE_PATH=data/warehouse/analytics.duckdb dbt build --profiles-dir dbt --project-dir dbt
```

### 8. Run tests

```bash
pytest tests/
```

### 9. Run the dashboard

Install the dashboard requirements if they are not already available:

```bash
pip install -r dashboards/requirements.txt
```

Then:

```bash
streamlit run dashboards/app.py
```

## Analytics marts

| Mart | Main use |
|---|---|
| `mart_sales` | Revenue, order status, and order-level sales metrics |
| `mart_customer_retention` | Cohorts, retention, and repeat-order metrics |
| `mart_product_performance` | Product sales and return rates |
| `mart_returns` | Return quantities, revenue impact, category, and region |
| `mart_inventory` | Inventory, reorder points, and days of cover |

## Data quality and reliability

Data quality is checked at multiple points in the pipeline instead of only at the dashboard layer.

The repository includes:

- dbt contracts and schema tests
- Grain tests for marts
- Negative tests for invalid relationships and statuses
- SCD2 historical-join tests
- SCD2 idempotency tests
- Watermark tests
- Retry/backoff tests
- Dashboard runtime guard tests
- Quarantine handling for malformed and invalid records
- Freshness monitoring in the dashboard

The raw ingestion path uses transactions so a failed batch does not leave a partially committed batch behind.

## Testing and verification

The latest engineering evidence report records:

- **224 dbt tests passing**
- **46 Python tests passing**, with 6 Postgres-dependent tests skipped when PostgreSQL is unavailable
- **1 Airflow DAG parse test passing**
- Ruff checks passing

The CI workflows run unit, integration, dbt, dashboard, Airflow-parse, and lint checks. The full integration workflow starts PostgreSQL as a GitHub Actions service.

Performance measurements in the repository were recorded against the deterministic seed dataset. See `docs/performance_benchmarks.md`.

## Current limitations

This is a local-first portfolio project rather than a production deployment.

Known limitations include:

- Airflow scheduler/webserver deployment is not included.
- Automated Airflow catch-up/backfill is not configured (`catchup=False`).
- Schema changes involving column removal, renaming, or type changes are not covered by migration tooling.
- The price anomaly check is tested but is not currently wired into the `obs_quality_checks` observability table.
- Late-arriving updates beyond the configured seven-day lookback are not stress-tested.
- DuckDB is used as a local warehouse and concurrent writers are not supported.

These are documented in more detail in `docs/limitations.md`.

## Architecture decisions

The major design choices are recorded as ADRs in `docs/adr/`.

The current architecture deliberately uses:

- DuckDB as the local analytical warehouse
- PostgreSQL as the OLTP source simulation
- Python for ingestion
- dbt for transformations, contracts, and tests
- Airflow for orchestration
- Streamlit for the read-only analytics interface
- Local files and synthetic data rather than external warehouse infrastructure

## Documentation

| Path | Purpose |
|---|---|
| `docs/architecture/` | Architecture and layer boundaries |
| `docs/adr/` | Architecture decision records |
| `docs/data_model/` | Data model and star-schema documentation |
| `docs/metrics_dictionary.md` | Metric definitions |
| `docs/data_quality_strategy.md` | Quality checks and responsibilities |
| `docs/lineage/` | Source-to-mart lineage |
| `docs/performance_benchmarks.md` | Measured performance |
| `docs/security_review.md` | Security review |
| `docs/privacy_review.md` | Privacy considerations |
| `docs/limitations.md` | Known limitations |

## License

No LICENSE file is currently included in the repository.
