# DataForge

DataForge is a local-first analytics engineering project for building a reproducible batch ELT pipeline from source data to analytics-ready datasets.

It combines Python ingestion, DuckDB, dbt, Apache Airflow, data-quality checks, dimensional modeling, and a Streamlit dashboard in one repository.

## Project overview

DataForge is built around a clear separation of responsibilities:

```
Source systems
    |
    v
Python ingestion
    |
    v
Raw layer (DuckDB)
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

The same pipeline can be orchestrated through the included Airflow DAG.

The project is intentionally local-first. PostgreSQL is used as an OLTP source simulation, while DuckDB is the analytical warehouse.

## Key capabilities

- Ingests CSV, NDJSON, REST API, and PostgreSQL sources
- Supports full and incremental loads
- Uses watermarks for incremental sources
- Uses batch IDs for repeatable ingestion
- Quarantines malformed records and invalid customer references
- Preserves raw records before business transformations
- Uses dbt staging, intermediate, core, and mart layers
- Includes an SCD2 customer dimension
- Enforces dbt model contracts and grain tests
- Tracks ingestion lineage and operational status
- Provides a marts-only Streamlit dashboard
- Includes Airflow orchestration and CI workflows
- Generates deterministic test data with configurable imperfections

## Source and load model

The repository currently defines eight sources:

| Source | Type | Processing |
|---|---|---|
| Customers | CSV | Full |
| Regions | CSV | Full |
| Orders | NDJSON | Incremental |
| Returns | NDJSON | Incremental |
| Products | REST API | Snapshot |
| Order items | PostgreSQL | Incremental |
| Payments | PostgreSQL | Incremental |
| Inventory levels | PostgreSQL | Incremental |

Incremental sources use a stored watermark. Each ingestion run receives a batch ID, and re-running a batch ID replaces its previous rows instead of creating another copy.

The raw layer keeps duplicate records for source fidelity. Deduplication is handled in downstream models where required.

## Data transformation

The dbt project follows:

```
staging
   ->
intermediate
   ->
core
   ->
marts
```

**Staging** handles source cleanup, casting, and normalization.

**Intermediate** models contain reusable business transformations.

**Core** models provide the analytical dimensions and facts, including the historical customer dimension.

**Marts** expose business-facing datasets for sales, retention, product performance, returns, and inventory.

## Dashboard

The Streamlit dashboard reads from the mart and observability layers only.

It currently includes:

- Sales and revenue trends
- Order counts and average order value
- Customer retention and cohorts
- Product performance
- Returns analysis
- Inventory and low-stock views
- Pipeline freshness and ingestion status

A runtime query guard prevents dashboard code from accidentally reading raw, staging, fact, dimension, intermediate, or information-schema relations.

## Airflow

The repository includes a daily Airflow DAG with the following flow:

```
Source ingestion
      ->
Raw validation
      ->
dbt snapshot
      ->
staging
      ->
intermediate
      ->
core
      ->
marts
      ->
quality checks
      ->
publish
```

The DAG defines retries, exponential backoff, execution timeouts, and a single active run.

The repository includes DAG parsing and dependency tests. An Airflow scheduler and webserver deployment are not included.

## Repository structure

```
DataForge/
├── ingestion/             # Extraction, watermarks, quarantine, loading
├── dbt/                   # dbt models, tests, macros, snapshots
├── airflow/               # Airflow DAG and DAG tests
├── dashboards/            # Streamlit dashboard
├── services/              # Local mock Products API
├── scripts/               # Seed data and utilities
├── configs/               # Seed configuration
├── tests/                 # Unit, integration, and dashboard tests
├── docs/                  # Architecture and engineering documentation
├── requirements/          # Dependency files
├── docker-compose.yml     # PostgreSQL source database
├── .env.example           # Local environment template
└── Makefile               # Common development commands
```

## Requirements

- Python 3.13
- Docker
- `uv` or pip

WSL2 is supported for the Windows Docker/PostgreSQL workflow.

The Python development dependencies are in `requirements/dev.txt`.

dbt and dashboard dependencies are installed separately because they are maintained as separate parts of the project.

## Getting started

### 1. Create the Python environment

Using the Makefile:

```bash
make venv
```

Or:

```bash
uv venv .venv --python 3.13
uv pip install -r requirements/dev.txt --python .venv/Scripts/python.exe
```

### 2. Configure the environment

Copy `.env.example` to `.env` and update the values for your local setup.

The default configuration uses:

```
PostgreSQL: localhost:5433
DuckDB:      data/warehouse/analytics.duckdb
Products API: http://localhost:8100
```

### 3. Generate the source data

```bash
python scripts/seed/generate_sources.py
```

The generated data and its imperfections are controlled by `configs/seed.yaml`.

### 4. Start PostgreSQL

```bash
docker compose up -d
python scripts/seed/populate_oltp.py
```

### 5. Start the Products API

The mock Products API is a separate FastAPI process.

```bash
uvicorn services.products_api.main:app --port 8100
```

It is not started by `docker compose`.

### 6. Initialize and load the warehouse

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

```bash
WAREHOUSE_PATH=data/warehouse/analytics.duckdb dbt build --profiles-dir dbt --project-dir dbt
```

### 8. Run the tests

```bash
pytest tests/
```

### 9. Start the dashboard

```bash
pip install -r dashboards/requirements.txt
streamlit run dashboards/app.py
```

## Analytics marts

| Mart | Purpose |
|---|---|
| `mart_sales` | Order-level sales and revenue metrics |
| `mart_customer_retention` | Cohorts, retention, and repeat orders |
| `mart_product_performance` | Product sales and return rates |
| `mart_returns` | Return volume and revenue impact |
| `mart_inventory` | Stock levels, reorder points, and days of cover |

## Data quality and reliability

The pipeline checks data at ingestion and transformation boundaries.

The repository includes:

- Structural and schema validation
- Referential-integrity checks
- Quarantine handling
- Watermark tracking
- Atomic batch loading
- dbt contracts
- Mart grain tests
- Negative data-quality tests
- SCD2 historical-join and idempotency tests
- Dashboard query-guard tests
- Freshness information in the dashboard

The ingestion loader commits a batch in a single transaction. A failed batch is rolled back and does not advance the corresponding watermark.

## Testing and CI

GitHub Actions provides separate fast and integration workflows.

The workflows cover:

- Ruff linting
- Python unit tests
- Dashboard tests
- Airflow DAG parsing
- dbt parsing/compilation
- Full integration runs with PostgreSQL
- Seed configuration validation

Performance measurements and reproducibility notes are documented under `docs/`.

## Limitations

DataForge is a portfolio and educational project, not a production deployment.

Current limitations include:

- Airflow scheduler/webserver deployment is not included.
- Airflow catch-up is disabled.
- Schema migration tooling is not included for destructive or incompatible schema changes.
- Price anomaly checks are tested but are not currently connected to the `obs_quality_checks` table.
- Late-arriving updates beyond the configured lookback window are not stress-tested.
- DuckDB is used as a local analytical warehouse and concurrent writers are not supported.

## Documentation

| Path | Contents |
|---|---|
| `docs/architecture/` | System architecture and layer boundaries |
| `docs/adr/` | Architecture decision records |
| `docs/data_model/` | Data model documentation |
| `docs/metrics_dictionary.md` | Metric definitions |
| `docs/data_quality_strategy.md` | Quality strategy |
| `docs/lineage/` | Source-to-mart lineage |
| `docs/performance_benchmarks.md` | Performance measurements |
| `docs/security_review.md` | Security review |
| `docs/privacy_review.md` | Privacy review |
| `docs/limitations.md` | Known limitations |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development checks and repository-specific contribution guidance.

## License

No LICENSE file is currently included in the repository.
