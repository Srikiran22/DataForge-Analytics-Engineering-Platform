# DataForge

DataForge is a local-first analytics engineering project for building a reproducible batch ELT pipeline from source data to analytics-ready marts.

The project is designed around a simple flow:

```
Source data
   |
   v
Python ingestion
   |
   v
Raw DuckDB layer
   |
   v
dbt transformations
   |
   v
Core models and marts
   |
   v
Streamlit dashboard
```

It supports both file-based and database sources, keeps raw data separate from transformed models, tracks ingestion state and lineage, and uses dbt tests and contracts to catch data-quality problems before they reach the dashboard.

## What it does

- Ingests CSV, JSON/NDJSON, REST API, and PostgreSQL sources
- Supports full and incremental loads using watermarks
- Assigns batch IDs so loads can be rerun safely
- Quarantines malformed or invalid records instead of silently dropping them
- Stores source data in a schema-on-read DuckDB raw layer
- Transforms data with dbt through staging, intermediate, core, and mart layers
- Maintains customer history with an SCD2 snapshot
- Builds analytics marts for sales, retention, products, returns, and inventory
- Records batch lineage and operational pipeline information
- Provides a read-only Streamlit dashboard over the marts
- Runs unit, integration, dashboard, and dbt tests in CI

## Architecture

### Sources

The project can work with:

- CSV files
- JSON/NDJSON files
- A mock products API
- PostgreSQL as an OLTP source

### Ingestion

The Python ingestion package handles extraction, validation, batch IDs, watermarks, quarantine, loading, and lineage.

A failed batch is not allowed to advance its watermark. This makes incremental ingestion easier to reason about and allows a failed load to be retried.

### Raw layer

DuckDB stores the raw records with ingestion metadata such as:

- `_batch_id`
- `_ingested_at`
- `_source_file`

Malformed records are kept in quarantine tables together with the reason for rejection.

The raw layer intentionally preserves source fidelity. Business transformations happen later in dbt.

### dbt

The dbt project is organized into:

```
staging
   -> intermediate
      -> core
         -> marts
```

Staging handles renaming, casting, and normalization. Intermediate models contain reusable business logic. Core models provide the analytical dimensions and facts. Marts expose the datasets used by the dashboard and business questions.

## Analytics marts

| Mart | Purpose |
|---|---|
| `mart_sales` | Revenue, order volume, and average order value |
| `mart_customer_retention` | Repeat purchases and cohort retention |
| `mart_product_performance` | Product-level performance |
| `mart_returns` | Return rates, reasons, and financial impact |
| `mart_inventory` | Inventory position |

## Technology

| Area | Technology |
|---|---|
| Ingestion | Python 3.13 |
| Warehouse | DuckDB |
| Source database | PostgreSQL 17 |
| Transformation | dbt |
| Orchestration | Apache Airflow |
| Dashboard | Streamlit |
| Testing | pytest, dbt tests |
| Linting | Ruff |
| CI | GitHub Actions |
| Environment | Docker / WSL2 supported |

Airflow is currently defined as part of the project but is not yet deployed as a production service. The warehouse itself is a DuckDB file rather than a separate database service.

## Getting started

### Requirements

- Python 3.13+
- Docker
- `uv` or pip
- WSL2 is recommended for the PostgreSQL/Docker workflow on Windows

### Install dependencies

```bash
uv pip install -r requirements/dev.txt
```

### Generate the source data

```bash
python scripts/seed/generate_sources.py
```

### Start PostgreSQL

```bash
docker compose up -d
```

Then populate the source database:

```bash
python scripts/seed/populate_oltp.py
```

### Initialize and load the warehouse

```bash
python -m ingestion.cli init-warehouse

python -m ingestion.cli load --source customers --full
python -m ingestion.cli load --source orders
python -m ingestion.cli load --source returns
python -m ingestion.cli load --source products
python -m ingestion.cli load --source regions
python -m ingestion.cli load --source order_items
python -m ingestion.cli load --source payments
python -m ingestion.cli load --source inventory_levels
```

### Build the dbt models

```bash
WAREHOUSE_PATH=data/warehouse/analytics.duckdb dbt build
```

### Run tests

```bash
pytest tests/
```

### Start the dashboard

```bash
streamlit run dashboards/app.py
```

## Repository layout

```
DataForge/
├── ingestion/        # Source extraction and loading
├── dbt/              # dbt models, tests, macros, and snapshots
├── dashboards/       # Streamlit dashboard
├── airflow/          # Airflow DAGs and tests
├── quality/          # Data contracts
├── scripts/          # Seed data and utility scripts
├── tests/             # Unit and integration tests
├── docs/              # Architecture, ADRs, data quality, and other documentation
├── requirements/      # Dependency definitions
├── docker-compose.yml # PostgreSQL source database
└── Makefile           # Project commands
```

## Data quality and reliability

The pipeline treats data quality as part of the load process rather than something checked only at the end.

Examples include:

- Schema and structural checks
- Required-field validation
- Foreign-key validation
- Accepted-value checks
- dbt uniqueness and not-null tests
- Batch lineage
- Watermark tracking
- Quarantine for rejected records
- Freshness checks
- Incremental model tests

The dashboard reads from analytics marts rather than directly from raw tables.

## Business questions

The current marts support questions such as:

- How is monthly revenue changing by region?
- What is the average order value over time?
- How many orders are in each status?
- What percentage of customers make repeat purchases?
- How does retention change across customer cohorts?
- Which products perform best?
- What are the main return reasons and their financial impact?
- What is the current inventory position?

## Testing

The repository contains unit, integration, dashboard, and dbt tests.

The documented baseline includes:

- 46 unique Python tests passed
- 6 Postgres-dependent tests skipped in environments without the source database
- 214 dbt tests passed
- dbt snapshot tests passing

Performance measurements and environment-specific results are documented in `docs/performance_benchmarks.md`.

## Current limitations

This is a portfolio and educational project, not a production deployment.

Known areas that still require environment-dependent verification include:

- Airflow scheduler/webserver deployment
- Airflow backfill testing
- Full-refresh versus incremental parity with newly introduced batches
- Adversarial late-arriving data scenarios
- Schema evolution scenarios
- Anomaly-detection wiring for the observability layer

These limitations are documented in more detail in `docs/limitations.md`.

## Documentation

| Document | Description |
|---|---|
| `docs/architecture/` | Pipeline architecture and layer contracts |
| `docs/adr/` | Architecture decision records |
| `docs/data_model/` | Table and star-schema documentation |
| `docs/metrics_dictionary.md` | Definitions for analytical metrics |
| `docs/data_quality_strategy.md` | Data-quality approach |
| `docs/lineage/` | End-to-end lineage examples |
| `docs/performance_benchmarks.md` | Measured performance |
| `docs/security_review.md` | Security review |
| `docs/privacy_review.md` | Privacy considerations |
| `docs/limitations.md` | Current limitations and future work |

## License

MIT. This repository is primarily intended as a portfolio and educational project.
