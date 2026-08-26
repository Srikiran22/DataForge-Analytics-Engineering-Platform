# ADR 0002: Orchestrator — Apache Airflow 3.x, single combined container (dev-grade config)

## Context
Spec §19 requires DAG-shaped orchestration (extract → load_raw → validate → dbt layers → quality → publish) with retries, timeouts, idempotent re-runs, backfill behavior. Hardware constraint: limited RAM/CPU. Verified facts (2026-08-26): Airflow stable = 3.3.1, Python 3.10–3.14 supported, **Airflow 2.x EOL since 2026-04-22**; SQLite is an officially supported metadata backend for the stable line (dev-grade). Self-hosted Airflow is acknowledged in current comparisons as the heaviest orchestrator (scheduler + webserver + metadata DB + executor).

## Options Considered
- **Airflow 3.3.x (SQLite metadata, SequentialExecutor, one combined scheduler+webserver container)** — pros: the industry-default orchestrator with the deepest ecosystem; strongest interview signal; DAG-file model maps cleanly onto the required pipeline shape; backfill/scheduling/retries built-in. cons: heaviest of the three even minimized (~hundreds of MB RSS); SequentialExecutor serializes task execution (fine — our workload is one daily batch); SQLite metadata DB is explicitly dev-grade, not production posture.
- **Dagster 1.13.x** — pros: asset-centric model is arguably the better fit for dbt-heavy platforms; native lineage/partitions; lighter than Airflow (2 processes). cons: second orchestration paradigm to learn and defend; smaller job-market presence than Airflow; would still need its daemon+webserver+run DB.
- **Prefect 3.x** — pros: lightest control plane; Pythonic flows. cons: deployment story centers work pools/cloud control plane — awkward for a fully-local compose stack; less common in analytics-engineering job specs.
- **Cron + Make** — pros: zero weight. cons: no retries/UI/backfill semantics; fails §19 outright; rejected without further debate (spec requires real orchestration).

## Decision
**Apache Airflow 3.3.x**, pinned, running as **one combined container** (spec §35 explicitly permits this for lightweight setups): LocalExecutor-free `SequentialExecutor` + SQLite metadata DB, single scheduler/webserver process pair inside the container. Business logic stays out of the DAG (hard rule §19) — tasks call `python -m ingestion...` modules and shell out to `dbt`.

Honesty note (repeated in README/limitations): this is a **deliberately dev-grade Airflow configuration**. The production upgrade path is mechanical, not architectural: swap SQLite→Postgres metadata DB, SequentialExecutor→LocalExecutor/CeleryExecutor, split containers.

## Trade-offs
Given up: parallel task execution within a run (irrelevant at one daily batch today); "production-grade" metadata store (documented, with migration path).

## Consequences
- Airflow's supported-Python matrix (3.10–3.14) constrains the image's Python → 3.12 chosen (inside every tool matrix).
- dbt is invoked via subprocess with its own pinned venv/requirements, decoupling Airflow constraints from dbt constraints (avoids the classic constraint-file collision).
- Backfill tests (§20) run against `catchup=True` semantics; catchup decision documented in the DAG itself.
- If RAM proves insufficient even for combined Airflow (measured, not assumed, in Phase 7), fallback documented: Prefect single-process — recorded here *before* building so the pivot is pre-justified rather than silent scope-cutting.
