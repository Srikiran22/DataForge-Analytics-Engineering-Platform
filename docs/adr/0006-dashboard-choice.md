# ADR 0006: Dashboard tool — Streamlit querying the warehouse directly

## Context
Spec §28 requires the dashboard to demonstrate the trust chain (dashboard ← trusted marts), with panels for revenue trend, retention, product performance, returns, inventory, and a data-freshness/pipeline-status panel fed by the observability layer. Tool choice must be justified in an ADR against Docker-friendliness and whether it queries the warehouse directly. Constraint: limited RAM/CPU.

## Options Considered
- **Streamlit 1.62 (Apache-2.0)** — pros: single lightweight Python process; connects directly to DuckDB (read-only) — every panel literally queries a mart, proving mart self-sufficiency (the spec's stated preference); trivial Dockerization; Python-only stack consistency. cons: it's an app framework, not a governed BI tool — no row-level security, no scheduled deliveries; layout polish takes code.
- **Metabase / Apache Superset** — pros: real BI semantics, drag-drop exploration. cons: JVM services, hundreds of MB to GBs of RAM each — disproportionate for ~7 panels; Superset additionally needs a metadata DB + init choreography. Both violate the resource envelope.
- **Evidence.dev** — pros: SQL-in-markdown analytics, static output. cons: Node toolchain in image; slower iteration loop; less common in AE job specs than either alternative.

## Decision
**Streamlit** app in one Compose service, connecting read-only to the DuckDB warehouse file, with a hard rule enforced in code review: **panels query marts/observability objects only** — never raw/staging tables (spec §27). The freshness/pipeline-status panel reads `obs_*` objects populated by the pipeline itself (§25/§38), making the trust chain visible rather than claimed.

## Trade-offs
Given up: BI-tool governance features and non-technical self-service exploration. At scale with analyst users, Metabase (lighter of the two BI options) becomes worth its RAM.

## Consequences
- Dashboard code lives in `dashboards/` with its own minimal requirements; it must degrade gracefully (visible staleness flag, §25) when the warehouse is mid-refresh or missing.
- Read-only connection mode is a security control as well as a safety rail (§32): the dashboard cannot mutate warehouse state even accidentally.
