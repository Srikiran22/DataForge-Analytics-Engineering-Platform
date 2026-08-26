# ADR 0004: Data-quality tooling — dbt tests + contracts + small custom statistical checks; no Great Expectations

## Context
Spec §17 requires checks across seven categories (schema, completeness, uniqueness, referential integrity, validity, freshness, distribution/anomaly) and explicitly instructs: justify Great Expectations honestly — if it adds nothing dbt tests can't do, say so rather than include it for the resume line. Verified context (2026-08-26): GX Core current = 1.21.0; GX was acquired by dbt Labs (announced 2026-05-06), GX Cloud shut down 2026-06-01, Fivetran now stewards OSS development after years of slowed maintenance during the GX Cloud era.

## Options Considered
- **Great Expectations 1.21** — pros: rich expectation catalog, statistical/distribution expectations out of the box, Data Docs; now has renewed corporate stewardship. cons: heavyweight dependency surface (pandas/pyarrow stacks) on RAM-constrained hardware; its own project/config paradigm to learn and maintain for what is, at our scale, a handful of anomaly checks; recent ownership churn is a real, stated risk factor.
- **dbt tests (generic + singular) + dbt model contracts + custom lightweight checks** — pros: one tool already in the stack covers schema (contracts), completeness/uniqueness/referential-integrity/validity (generic tests), business rules (singular tests), freshness (source freshness); custom distribution/anomaly checks are ~50 lines of Python/SQL against DuckDB with results written to the observability mart. Zero new dependencies. cons: we own the anomaly-check code; no Data Docs UI (our observability panel replaces it).

## Decision
**Do not adopt Great Expectations.** Division of labor:
| Category | Owner |
|---|---|
| Schema | dbt model contracts (`enforced: true`, marts minimum) + raw-layer contract validation script (§16) |
| Completeness / uniqueness / relationships / validity | dbt generic tests |
| Business rules (e.g., net_revenue ≤ gross_revenue) | dbt singular tests |
| Freshness | dbt source freshness |
| Distribution/volume anomalies | custom Python check module writing to `obs_quality_checks` (part of observability, §25) |

This mapping is restated in `docs/data_quality_strategy.md` and every check traces to a row in `docs/data_imperfections.md`.

## Trade-offs
Given up: GX's prebuilt expectation suite breadth and Data Docs rendering. We accept writing and maintaining a small number of statistical checks ourselves.

## Consequences
- If anomaly-checking needs grow beyond simple volume/value drift (e.g., per-segment distributions across many columns), this decision gets revisited — trigger documented here.
- The custom checker must meet the same bar as any component: unit-tested, idempotent, failures surfaced in the pipeline (not logged-and-lost).
- Re-evaluation note: Fivetran/dbt stewardship may fold GX capabilities closer to dbt itself; watch item, not a reason to adopt today.
