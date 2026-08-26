# ADR 0003: Transformation tool — dbt-core 1.12 with dbt-duckdb adapter

## Context
The platform needs a transformation layer owning staging/intermediate/mart SQL, tests, snapshots (SCD2), docs/lineage generation, contracts, and incremental models (spec §8, §11–§16, §21). Verified (2026-08-26): dbt-core active-support line = 1.12 (released 2026-07-16; supported until 2027-07-15); dbt 2.0 exists only as beta; dbt-duckdb 1.11.0 pairs with dbt-core `>=1.12.0,<2`.

## Options Considered
- **dbt-core + dbt-duckdb** — pros: de-facto standard for exactly this job: tests-as-config, snapshots for SCD2, model contracts (`contract: enforced`), source freshness, generated DAG/docs (feeds our lineage story §24), incremental strategies including native `merge`; huge hiring-market alignment. cons: Jinja learning curve; another version-lock to manage.
- **Hand-written SQL scripts orchestrated by Python** — pros: zero dependencies, full control. cons: we would rebuild tests, lineage, docs, snapshots, and incremental handling badly by hand — precisely the "silent scope reduction" trap; rejected.
- **SQLMesh** — pros: modern alternative with strong virtual-environment/state ideas. cons: smaller ecosystem/hiring signal than dbt for an analytics-engineering portfolio piece; no capability gap vs dbt that our spec requires. Rejected on ecosystem-fit grounds.

## Decision
**dbt-core ~1.12 pinned together with dbt-duckdb ~1.11**, locked in a dedicated requirements file; versions verified side-by-side via `dbt --version` at setup. Layer convention: **folder-per-domain within each layer** (`staging/{source_oltp,api,...}`), documented in the dbt README.

## Trade-offs
Given up: full control over SQL execution order/machinery (we accept dbt's manifest-driven DAG); some Jinja indirection in exchange for tested, reusable patterns.

## Consequences
- Every generic test, snapshot config, contract, and freshness threshold is expressed in dbt-native config → the quality layer (§16–18) leans on one tool's semantics rather than a homegrown runner.
- Model contracts enabled at least on marts (§15) give compile-time schema guarantees feeding ADR 0004's division of labor.
- Version-bump procedure: bump core+adapter atomically, run `dbt parse` + full build + test suite before merging — codified in CI (Phase 10).
