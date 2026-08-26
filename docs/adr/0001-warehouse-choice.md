# ADR 0001: Warehouse choice — DuckDB for analytics, PostgreSQL as OLTP source only

## Context
The platform needs a warehouse for the star-schema/mart layers and at least one relational source system acting as a realistic OLTP database (spec §3.1). Hard constraints: local Docker Compose on hardware with **limited RAM/CPU**; reproducibility on a clean machine is a spec-level requirement (§0.8); the dbt project must be swappable to a cloud warehouse via profile changes only (§1.2).

## Options Considered
- **DuckDB as warehouse** — pros: in-process file DB (zero services to run), excellent analytical SQL + columnar performance at our volume (tens of thousands to low millions of rows), first-class dbt adapter actively maintained under the duckdb org, native `MERGE` incremental strategy (DuckDB >= 1.4), trivial reproducibility (file regenerable from seeds). cons: single-writer (no concurrent writers), not a production multi-user DW, some SQL/functions are DuckDB-flavored.
- **PostgreSQL as warehouse** — pros: closest to "real production" ops experience, concurrent readers/writers, mature dbt-postgres adapter. cons: a always-running service consuming RAM we don't have to spare; row-store performance irrelevant-to-negative at analytics volumes; more setup/backup friction for zero benefit here.
- **Cloud DW (Snowflake/BigQuery/Databricks)** — pros: what enterprises actually run. cons: cost, credentials, network dependency — directly violates local-reproducibility rule §0.8. Non-starter.

## Decision
**DuckDB 1.5.x is the analytics warehouse.** A small **PostgreSQL 17 container exists solely as the simulated OLTP source** (`source_oltp` schema: customers/orders/payments tables) so the relational-source shape is real. The dbt project connects via `dbt-duckdb`.

> Portability status (2026-08-26): warehouse swap via profile change is an **intent, not a demonstrated property**. It may not be claimed as achieved until an actual compatibility check runs (e.g., `dbt-parse`/build of this project against `dbt-postgres` on a test schema) and the result is recorded here or in a successor ADR. Until then, all docs must phrase migration as planned-and-unverified.

Portability guardrails enforced from Phase 4:
- Models use ANSI SQL; any DuckDB-specific function must be isolated in a macro with a dispatch override.
- Any model that would need changes on migration gets flagged in its schema.yml description.

## Trade-offs
Given up: multi-user concurrency realism and "operating a real DB service" experience at the warehouse layer; some DuckDB-specific SQL temptation.

## Consequences
- No warehouse container in Compose → RAM budget freed for Airflow/dashboard.
- Single-writer assumption must be stated everywhere scale is discussed (§41); concurrent dashboard reads of the DuckDB file use read-only mode.
- The Postgres source container doubles as our practice surface for least-privilege roles (§32) — read-only ingestion user vs admin.
- Migration trigger documented: sustained >~50M rows/fact or true multi-writer need → revisit (likely Postgres first, cloud DW when cost justifies).
