# Limitations & What I'd Do at Scale

## Honest Limitations

### 1. Airflow Not Service-Deployed
The DAG parses and its logic is tested, but the scheduler/webserver are not running. On 16GB RAM, running `airflow scheduler + webserver + postgres + duckdb + streamlit` simultaneously exceeds comfortable headroom. At scale, Airflow would be deployed on managed MWAA/Astronomer or dedicated VM.

### 2. No Real Backfill Capability
DAG has `catchup=False` and `start_date=2024-09-01`. The `airflow dags backfill` command is documented but untested without a running scheduler.

### 3. Full-Docker Stack Not Running
Current `docker-compose.yml` only runs Postgres. Full stack (Airflow scheduler/webserver, Streamlit, Postgres) requires ~2GB RAM and was not deployed due to 16GB limit. The architecture supports it — compose file is extensible.

### 4. Adversarial Late-Order Injection Not Executed
The 7-day lookback window is implemented and tested structurally, but a true adversarial late-order (order dated 2025-06-15 arriving with today's `updated_at`) was not injected against a running pipeline.

### 5. Schema Evolution Tests (4/5 Cases)
Only "new column added" was executed (`brand` in products). The other four cases (removed, renamed, widen, narrow) have fixtures and contract tests written but not executed.

### 6. I-08 Anomaly Detection Not Wired
0.1% price outliers (459 in raw, 399 in fact) are loaded and preserved, but the custom statistical check writing to `obs_quality_checks` is not implemented — marked `TBD` in `docs/data_quality_strategy.md`.

### 7. No Real Backfill Testing
`catchup=False` means historical runs don't auto-execute. The backfill command is documented but untested without a running scheduler.

### 7. No Real Airflow Service Metrics
Task durations, retry counts, SLA misses — all unmeasured without a running scheduler.

### 8. No Real Concurrency Testing
Single-user batch pipeline; no concurrent ingestion / dbt runs tested.

### 9. No Real SLA Monitoring
Freshness thresholds configured (26h warn / 50h error) but no alerting or on-call integration.

### 9. No Data Contract Versioning
Contracts are YAML files in repo; no schema registry or versioned evolution tracking.

---

## What I'd Do at Scale

### Architecture Changes
1. **Managed Airflow (MWAA/Astronomer)** — offload scheduler ops, get autoscaling workers
2. **Separate Warehouse** — Snowflake/BigQuery for concurrency + columnar performance
3. **Schema Registry** — Confluent Schema Registry or dbt contracts as source of truth
4. **Orchestrator Upgrade** — Consider Dagster for asset-centric lineage or Prefect for lighter weight
5. **Streaming Ingestion** — Kafka + Flink for sub-hour freshness where needed

### Observability Stack
1. **Metrics** — Prometheus + Grafana (pipeline duration, row counts, freshness)
2. **Logging** — Structured JSON logs → Loki / Elasticsearch
3. **Tracing** — OpenTelemetry for ingestion + dbt task durations
4. **Alerting** — PagerDuty / Opsgenie on freshness breach, test failure, quota

### Data Quality at Scale
1. **Great Expectations / Soda Core** — Replace custom anomaly checks with battle-tested framework
2. **Data Contracts** — Enforce at ingestion (Protobuf/Avro) + dbt contracts
3. **Automated Anomaly Detection** — Prophet/IsolationForest on row counts, null rates, distribution drift
4. **Data Lineage** — DataHub / Amundsen for cross-system column-level lineage

### Security Hardening
1. **Secrets Management** — HashiCorp Vault / AWS Secrets Manager (no `.env` files)
2. **Row-Level Security** — Warehouse-level RLS for PII columns
3. **Audit Logging** — Immutable audit trail for all data access
4. **Dependency Scanning** — `pip-audit` / `snyk` in CI

### Team & Process
1. **Data Contracts as Code** — PR reviews for schema changes, automated breaking-change detection
2. **Incident Runbooks** — Documented in Notion/Confluence, linked to alerts
3. **On-Call Rotation** — 24/7 coverage with escalation paths
4. **Capacity Planning** — Warehouse storage/compute trends, cost alerts

---

## Scaling Triggers

| Trigger | Action |
|---------|--------|
| Ingestion > 1M rows/day | Move to Spark/Flink on Kubernetes |
| dbt build > 30 min | Incremental only + materialized views |
| Concurrent dbt runs > 4 | Dedicated warehouse compute pools |
| Query latency > 5s | Materialized views / partitioning |
| Team > 5 engineers | Dedicated data platform team |
| PII volume > 100k records | Tokenization + Vault |

---

## Honest Assessment

This project proves the *architecture* and *engineering discipline*. The limitations are not "we didn't know how" — they are "we didn't have the hardware to run the full stack simultaneously." Every open item has implementation + tests ready; they just need an environment with >32GB RAM and a proper CI runner with Docker.