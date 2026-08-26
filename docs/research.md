# Phase 0 Research — Verified Version Matrix

**Verification date: 2026-08-26** (all versions checked live via official release pages on this date; re-verify before upgrading anything).

Rule honored: no version in this document was recalled from memory — each row cites its source. Anything not yet verified is marked `TBD`.

## 1. Tooling version matrix

| Tool | Chosen/pinned | Current stable (verified) | Verified | Source | Notes |
|---|---|---|---|---|---|
| Python | 3.12.x | 3.14.7 (latest feature series, 2026-08-05); 3.13.15; 3.12.14 maintained | 2026-08-26 | python.org downloads + Python Insider blog | We target **3.12**: the conservative intersection of every tool's supported matrix below. 3.13/3.14 are supported by Airflow 3.3 but dbt-core 1.12's upper Python bound is not yet verified by us — will confirm empirically at first install (Phase 2) and record the result. |
| DuckDB (warehouse) | 1.5.x (pin 1.5.5) | 1.5.5 (2026-07-22); 1.4.5 LTS; 2.0.0 scheduled Fall 2026 | 2026-08-26 | duckdb.org/release_calendar, github.com/duckdb/duckdb/releases | `merge` incremental strategy in dbt-duckdb requires DuckDB >= 1.4.0. 2.0.0 is a watch item, not an adoption target. |
| PostgreSQL (OLTP source only) | 17.x | 18.6 current major (2026-08-13); supported: 18, 17, 16, 15, 14 | 2026-08-26 | postgresql.org/about/news (2026-08-13), versioning policy page | Used **only** as the relational OLTP source system, not the warehouse (see ADR 0001). PG 17 chosen over 18 for maturity margin; both are supported. |
| dbt-core | ~1.12 (active-support line) | 1.12 (2026-07-16, active support until 2027-07-15); 2.0 in beta | 2026-08-26 | docs.getdbt.com/docs/dbt-versions | **Do not adopt dbt 2.0 (beta).** Known recent breakage: dbt-adapters 1.24.0 (JS UDF macro change) caused parse-time KeyError on older cores in May 2026; fixed by dbt-core 1.11.11+. Pinning avoids exposure. |
| dbt-duckdb (adapter) | ~1.11 | 1.11.0 (2026-08-07) | 2026-08-26 | github.com/duckdb/dbt-duckdb/releases | Repo changelog shows dbt-core requirement moved to `>=1.12.0,<2` before this release. Behavior change in 1.11.0: `partitioned_by` entries are emitted as-written (no auto-quoting). Will confirm the effective pin with `dbt --version` + `pip check` at install time. |
| Apache Airflow | 3.3.x (pin 3.3.1) | 3.3.1 (2026-08-12) | 2026-08-26 | airflow.apache.org docs (stable), apache.googlesource README | Supports Python 3.10–3.14. **Airflow 2.x reached EOL 2026-04-22** — starting on 3.x avoids inheriting a dead major version. SQLite is an officially supported metadata DB for the stable line (dev-grade; see ADR 0002). |
| Great Expectations | NOT adopted | 1.21.0 (2026-08-19) | 2026-08-26 | pypi.org/project/great-expectations, greatexpectations.io blog | Acquired by dbt Labs (announced 2026-05-06); GX Cloud shut down 2026-06-01; Fivetran is steward of GX Core OSS. Project revived but heavyweight for our needs — rejection rationale in ADR 0004. |
| OpenLineage / Marquez | NOT adopted (Marquez infra) | Marquez last release 0.50.0 (2024-10-24); repo receives maintenance pushes (Jul 2026), OpenLineage spec active | 2026-08-26 | github.com/MarquezProject/marquez | ~22 months without a release. Running a Java metadata server for 4 sources fails the "every technology justifies itself" test — see ADR 0005. |
| Streamlit (dashboard) | ~1.62 | 1.62.0 (2026-08-19) | 2026-08-26 | pypi.org/project/streamlit, github.com/streamlit/streamlit/releases | Apache-2.0, Python >= 3.10, single lightweight process. Chosen over Metabase/Superset/Evidence — ADR 0006. |
| GitHub Actions: `actions/checkout` | @v7 | v7 current major | 2026-08-26 | github.com/actions/setup-python README (examples updated to v7), releases pages | v5 went node24 (Aug 2025); v6 required runner >= 2.327.1; v7 current. |
| GitHub Actions: `actions/setup-python` | @v7 | v7 current major (v7.0.0) | 2026-08-26 | github.com/actions/setup-python/releases | v7 migrated internals to ESM; inputs unchanged. |
| Docker Compose | Compose Specification (v2 CLI, `docker compose`) | Spec is the canonical syntax; no pinned version number needed | 2026-08-26 | docs.docker.com/compose/compose-file/ | Use `docker compose` (plugin) syntax throughout; healthchecks + `depends_on.condition` per spec. |
| Dagster (evaluated) | rejected | 1.13.17 core / 0.29.17 libs (2026-08-07) | 2026-08-26 | github.com/dagster-io/dagster/releases | See ADR 0002. |
| Prefect (evaluated) | rejected | 3.x line | 2026-08-26 | modern-datatools comparison, prefect docs | See ADR 0002. |

## 2. Compatibility lock analysis (the classic breakage points)

1. **dbt-core ↔ dbt-duckdb**: dbt-duckdb 1.11.0 declares `dbt-core >=1.12.0,<2`. Lock both together in `requirements/dbt.txt`; verify with `dbt --version` (core + plugin reported side-by-side) at env setup. Never bump one without the other.
2. **Airflow ↔ Python**: Airflow 3.3.1 supports Python 3.10–3.14 → Python 3.12 is safely inside the matrix. Install Airflow **with its constraints file** for the exact AIRFLOW_VERSION × PYTHON_VERSION pair (documented install command in the Airflow quick start), which prevents transitive-dependency drift.
3. **dbt-duckdb ↔ duckdb**: adapter targets `duckdb >= 1.0.0`; `merge` strategy needs DuckDB >= 1.4.0. We pin duckdb 1.5.5 → both satisfied.
4. **Airflow ↔ dbt co-location**: we deliberately do **not** install dbt inside the Airflow image's same Python env if constraints conflict; Airflow tasks shell out to `dbt` via `BashOperator`/virtualenv boundaries. Decision detail in ADR 0002/0003 consequences.

## 3. Breaking / notable changes in the last 12 months (Aug 2025 → Aug 2026)

| Window | Change | Impact on us |
|---|---|---|
| Sep 2025 | PostgreSQL 18 released | None — we're on 17 as source-only. |
| Oct 2025 | Python 3.14 feature release | Not adopted; 3.12 target unaffected. |
| Apr 2026 | Airflow 2.x EOL | Forced the 3.x decision; all DAG code written against Airflow 3 APIs from day one. |
| Mar 2026 | DuckDB 1.5.0 "Variegata"; 1.4.x declared LTS | We ride 1.5.x patch line; LTS available as fallback. |
| May 2026 | dbt-adapters 1.24 broke older dbt-core parsing (JS UDFs); fixed in dbt-core 1.11.11 | Reason to pin >= 1.11.11-equivalents; our 1.12 pin postdates the fix. |
| May–Jun 2026 | GX acquired by dbt Labs; GX Cloud shutdown; Fivetran stewardship | Stewardship risk factored into rejecting GX (ADR 0004) — though weight alone was decisive. |
| Jul 2026 | dbt-core 1.12 released (active support); dbt 2.0 beta exists | Adopt 1.12 stable line; ignore 2.0 until GA + adapter parity. |
| Aug 2026 | Airflow 3.3.x adds Coordinator layer (AIP-108) etc. | No impact at our scale; noted for awareness. |
| ongoing | GH Actions major bumps (checkout v5→v7, setup-python v6→v7) | Workflows will pin @v7 from the start. |

## 4. Hardware-constraint-driven posture

Environment reality (user-stated): Docker available, **limited RAM/CPU**. Consequences applied across decisions:

- Warehouse = in-process DuckDB file (no warehouse service at all).
- One Postgres container, sized small, serving only the fake OLTP source schema.
- Airflow as a single combined container (SQLite metadata DB, SequentialExecutor) — documented honestly as dev-grade; scaling path stated in ADR 0002.
- Streamlit (single Python process) instead of JVM BI servers.
- Total steady-state footprint target: well under 2 GB across all containers.

## TBD (explicitly unverified)

- Exact `requires-python` bounds of dbt-core 1.12 (will be confirmed empirically at first install; 3.12 chosen to stay safe regardless).
- Effective installed pairing report of dbt-core × dbt-duckdb × duckdb (produced by `dbt --version` in Phase 2 and recorded there).
