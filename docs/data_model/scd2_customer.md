# SCD2 Customer — Verification Log

## Columns
`dbt_valid_from` / `dbt_valid_to` / `is_current` / surrogate `customer_sk` per spec §8.

## Scenarios

| # | Scenario | How Induced | Observed | Pass? |
|---|----------|-------------|----------|-------|
| 1 | City change → old `is_current=false` + `dbt_valid_to` set, new row `is_current=true` | Snapshot on synthetic history with mutated `city` for `C000001` (custom fixture) | 2 versions in `analytics.snap_customer` for `C000001` | PASS (test `snap_scenario_01_city_change` — 0 failures) |
| 2 | Region+segment change in same batch → ONE new version | Single `updated_at` mutation of both attrs | `dbt_hashdiff` dup check `snap_scenario_02` — 0 failures | PASS |
| 3 | Order before address change joins to version valid AT order time | `fct_orders` SCD2 join `o.order_ts >= c.dbt_valid_from AND (c.dbt_valid_to IS NULL OR o.order_ts < c.dbt_valid_to)` | `snap_scenario_03_historical_join` — 0 join fan-outs (each order maps to exactly 1 dim row) | PASS |
| 4 | Unchanged rerun → 0 new rows | `dbt snapshot` run twice on unchanged `stg_customers` | Both runs `PASS=1`, rowcount stable at 40,000 | PASS |

## Supporting Evidence

```
dbt snapshot — PASS (run 1)
dbt snapshot — PASS (run 2, idempotent)
dbt build — dim_customer view OK (40,000 current rows)
SELECT COUNT(*) FROM analytics.snap_customer — 40,003 versions (≈0.007% history due to synthetic mutations)
```

## Remaining Risk

Synthetic history has minimal mutations by design; production-like churn is not stress-tested until Group 5 adversarial suite with forced mutations.