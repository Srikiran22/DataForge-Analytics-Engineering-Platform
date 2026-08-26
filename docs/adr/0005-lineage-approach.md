# ADR 0005: Lineage approach — dbt-generated graph + ingestion lineage log; no Marquez server

## Context
Spec §24 requires concrete source → dashboard lineage for at least one full chain, permits judging full lineage infra too heavy at this scale if documented as an ADR, and demands the maximum useful free lineage otherwise. Verified (2026-08-26): Marquez's latest release is **0.50.0 from 2024-10-24** (~22 months stale; repo sees only maintenance pushes); OpenLineage as a *specification* remains active. Running Marquez means another always-on Java service + backing DB.

## Options Considered
- **OpenLineage + Marquez** — pros: industry-standard event spec; end-to-end lineage including ingestion jobs if instrumented; real UI. cons: Java service + Postgres container for 4 sources = RAM spend against our constraint; upstream release dormancy raises operational risk of chasing integration bugs alone; Airflow 3 × OpenLineage provider compatibility adds another moving part for marginal value at this scale.
- **dbt docs generate (transformation graph) + custom ingestion-lineage table** — pros: `dbt docs generate` yields a real, browsable DAG covering staging→marts for free; a tiny `lineage.batch_lineage` table (batch_id, source_name, source_ref, target_raw_table, ingested_at, row_count) populated by the ingestion loader closes the source→raw gap dbt can't see; upgrade path is honest and short. cons: no single unified UI spanning ingestion+transform; manual join between the two views.

## Decision
**Lightweight approach**: (1) dbt-generated model graph + column-level documentation treated as a deliverable (descriptions mandatory, §15); (2) ingestion writes structured lineage rows per batch into DuckDB; (3) one fully-traced chain (`orders.csv` → raw → staging → int → `fct_orders` → `mart_sales`) documented end-to-end in `docs/lineage/`; (4) upgrade path recorded: at more sources/higher cadence, adopt OpenLineage instrumentation emitting to a hosted/managed catalog rather than self-hosting Marquez.

## Trade-offs
Given up: automated unified cross-tool lineage UI. We keep the same information, split across two queryable surfaces.

## Consequences
- Ingestion loader API must emit lineage events as a first-class side effect (design input for Phase 2, not an afterthought).
- The traced chain becomes a maintained artifact: re-verified whenever the flow changes (same rule as the architecture diagram).
