# Data Quality Strategy

## Violation → Action (spec §18)

| Type | Example | Action | Evidence |
|------|---------|--------|----------|
| Structural break (missing column) | source file wrong schema | Fail pipeline | `dbt build` fails on contract mismatch |
| Record-level recoverable | invalid FK, malformed JSON | Quarantine → load rest + alert | `raw.quarantine_orders` 1,738 rows, `raw.quarantine_returns` 23 |
| Soft validity | price 0 or >20× median | Continue with warning | 0.1% outliers flagged, still loaded (custom check pending) |
| Duplicate | exact replay | Dedup silently + log count | `skipped_replayed` counted, staging `ROW_NUMBER()` keeps latest |

## Tool Assignment (spec §17)

| Category | Tool | Why |
|----------|------|-----|
| Schema | dbt contracts (`enforced`) | Compile-time guarantees on marts |
| Completeness | dbt `not_null` per BQ-mapped column | |
| Uniqueness | dbt `unique` on PKs | |
| Referential | dbt `relationships` tests | |
| Validity | `accepted_values` + custom singular tests | e.g. `assert_net_le_gross` |
| Freshness | dbt source `freshness` (26h warn / 50h error) | Feeds `mart_observability` freshness panel (Group 3) |
| Anomaly | custom Python distribution check → `obs_quality_checks` | *Deferred to Group 3 observability layer; TBD until measured* |

## Imperfection → Mechanism Map

| I | Imperfection | Layer that catches | Proving test |
|---|--------------|--------------------|--------------|
| I-01 | 3% missing email | staging (nullable) | `not_null` removed on `dim_customer.email` — passes 1,162 nulls |
| I-02 | 1% duplicate orders | watermark `skipped_replayed` + staging `ROW_NUMBER()` + `unique` on fct | `skipped_replayed` >0, 2,481 dup pairs preserved in raw |
| I-03 | 0.5% invalid FK customer | `raw.quarantine_orders` (reason `invalid_fk_customer`) | 1,215 quarantined, 0 leak to facts |
| I-04 | 0.2% malformed JSON | `raw.quarantine_*` (reason `malformed_json`) | 523 + 23 quarantined |
| I-05 | New column `brand` in API v2 | `warn+adapt` (missing → NULL) | 8,000 products have brand post-drift |
| I-06 | 2% late payments (backdated) | 7-day lookback in incremental `where` | watermark lookback 7 days |
| I-07 | Inconsistent category casing | `stg_products.lower(category)` | 6 variants collapsed to lower |
| I-08 | 0.1% price outliers | custom anomaly check | *TBD — implementation in Group 3 obs table* |

All 9 imperfections have a traced mechanism. Anomaly detection is the sole `TBD`.