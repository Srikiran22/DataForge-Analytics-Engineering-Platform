# Schema Evolution Policy (spec §23)

| Change | Policy | Reason | Test |
|--------|--------|--------|------|
| New column added | Warn + adapt (ignore extra unless mapped) | Non-breaking | I-05 `brand` — v1 NULL, v2 populated; `dbt build` PASS |
| Column removed | Fail contract | Downstream dependency — silent NULL worse than clear failure | *Fixture test deferred to Group 5 resilience suite* |
| Column renamed | Fail contract (looks like remove+add) | Cannot auto-detect intent | *Same deferred fixture* |
| Type widening (int→bigint) | Warn, adapt | Non-breaking | *TBD* |
| Type narrowing/incompatible | Fail contract | Truncation/corruption risk | *TBD* |

## Current Evidence

- **New column**: `brand` added 2026-02-01. Verified: `SELECT count(*) FROM main_analytics.dim_product WHERE brand IS NOT NULL` = 8,000. Pipeline did NOT fail; contract allowed `brand` nullable → `warn+adapt` proven.
- **Removed/renamed/type-change**: Simulated fixtures and contract-failure tests are planned for Group 5 adversarial suite. Per evidence rule, marked `TBD` until executed.

## Upgrade Path

Removed/renamed columns trigger `dbt build` failure via `on_schema_change: append_new_columns` + contract mismatch. Team fixes schema.yml + model SQL in a reviewed PR before merge — no silent data corruption.