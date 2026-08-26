# Data Imperfection Injection Log

**Purpose (spec §3.2):** proof that the data-quality layer is not decorative. Every row here is a defect we deliberately inject, with the specific mechanism expected to catch/handle it. Conversely: every quality check written in later phases must trace back to a row in this table — a check with no imperfection behind it needs justification of its own.

All injections are produced by the seeded generator or versioned fixtures — reproducible, never hand-edited.

## Injection table

| # | Imperfection | Source(s) affected | Injection method | % affected | Layer expected to catch/handle | Specific mechanism |
|---|---|---|---|---|---|---|
| I-01 | Missing email (null) | `customers.csv` (S1) | seed generator flag | ~3% | staging | nullable column in `stg_customers`; completeness threshold test (null rate ≤ 5%) rather than hard not_null |
| I-02 | Duplicate orders from batch replay (same `order_id` re-delivered) | `orders.json` (S3) | replay simulation: ~1% of a day's records reappear in the next day's file — half as byte-identical copies, half as mutated copies with advanced `updated_at` | ~1% of orders | raw → staging | two-path handling: (a) identical redeliveries are watermark no-ops, skipped at extraction and counted (`skipped_replayed`); (b) mutated re-deliveries land as a second version in raw (fidelity preserved), staging dedups via `ROW_NUMBER()` keeping max(`updated_at`); dbt `unique` test proves one current row per order downstream |
| I-03 | Invalid foreign key (order references nonexistent customer) | `orders.json` (S3) | seed generator flag | ~0.5% | raw load + warehouse tests | quarantine routing at raw layer (reason recorded), record excluded from staging; referential-integrity test on fact proves none leaked |
| I-04 | Malformed JSON line (unparseable) | `orders.json`, `returns.json` (S3/S4) | generator writes corrupted line (truncated object) | ~0.2% of lines | ingestion | parse-failure handler quarantines the line with error detail; pipeline continues; count surfaces in observability |
| I-05 | Schema drift — new column added mid-stream (`brand` appears in API v2) | `products` API (S5) | versioned fixture files v1→v2; mock switches versions on a fixed date | one-time event | raw contract check | documented policy §23: warn + adapt (extra column ignored unless mapped); contract test asserts pipeline does NOT fail and data still loads |
| I-06 | Late-arriving payment (payment event lands days after its order date, backdated event timestamp) | OLTP `payments` (S6) | seed generator backdating flag | ~2% | incremental model logic | incremental lookback window wide enough for max assumed lateness (7 days, justified Phase 2/21); reconciliation test: payment totals match regardless of arrival order |
| I-07 | Inconsistent category casing / synonyms (`electronics`, `Electronics`, `ELECTRONICS`) | `products` API (S5) | generator casing randomizer | mixed across records | staging | normalization mapping in `stg_products` (casing fold + synonym table); accepted_values test passes only post-normalization |
| I-08 | Soft validity outlier (unit price outside plausible range, e.g. 0 or > 20× median) | OLTP `order_items` (S6) | seed generator outlier flag | ~0.1% | intermediate/mart quality checks | custom statistical anomaly check flags to `obs_quality_checks`; rows still load (soft issue = continue with warning per §18 decision table) |
| I-09 | Duplicate customer email across two different `customer_id`s | `customers.csv` (S1) | seed generator flag | ~0.3% | staging tests | uniqueness scoped correctly: `customer_id` unique (hard test), email NOT globally unique (documented); flagged via singular test as reviewable warning |

## Mapping to the §18 violation-type decision table

| Violation type | Injected by |
|---|---|
| Structural/contract break ⇒ **fail pipeline** | induced in reliability tests (§20) by serving a products fixture with a *removed required column* (test scenario, not part of steady-state seeds) |
| Record-level recoverable ⇒ **quarantine + continue** | I-03, I-04 |
| Soft validity ⇒ **warn + continue** | I-08, I-09 |
| Exact duplicate ⇒ **dedup silently + log count** | I-02 |

## Coverage check against §17 quality categories

| Category | Proven exercise by |
|---|---|
| Schema | I-05 (+ structural-break failure test) |
| Completeness | I-01 |
| Uniqueness | I-02, I-09 |
| Referential integrity | I-03 |
| Validity | I-07, I-08 |
| Freshness | exercised via source-freshness config + staleness panel (mechanism exists independent of injection; verified in Phases 6–7) |
| Distribution/anomaly | I-08 |

## Status discipline

Each mechanism above gets an automated test in Phases 2–7. Until then its proving test is **planned**, not passing. The Phase 6 gate explicitly requires: every I-row has a passing test demonstrating detection. Nothing in this table counts as evidence until that log entry exists.
