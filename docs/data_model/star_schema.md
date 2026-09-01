# Star Schema Design

## Why Star Schema

Chosen over snowflake and 3NF for the mart layer because:

| Factor | Star | Snowflake | 3NF |
|--------|------|-----------|-----|
| Query simplicity | ✅ Single join per dimension | ❌ Multiple joins | ❌ Complex joins |
| BI tool friendliness | ✅ Native support | ⚠️ Requires views | ❌ Not native |
| Denormalization cost | Low (dimensions small) | N/A | N/A |
| Conformed dimensions | ✅ Enforced | ✅ Enforced | ❌ Not guaranteed |
| Mart query performance | ✅ Optimal for aggregation | ⚠️ Extra joins | ❌ Slow |

**Trade-off**: Accept denormalization in dimensions (e.g., `region_name` duplicated in `dim_customer` via FK) for query simplicity and BI-tool friendliness. Dimension tables are small (customers 40k, products 8k, regions 12, dates ~3k) — redundancy is negligible.

## Conformed Dimensions

All facts share the same dimension instances:

| Dimension | Used By |
|-----------|---------|
| `dim_customer` (SCD2) | `fct_orders`, `fct_order_items`, `fct_payments`, `fct_returns` |
| `dim_product` | `fct_order_items`, `fct_returns` |
| `dim_date` | All facts |
| `dim_region` | `dim_customer` (via FK), regional rollups |

No per-mart reinvented date logic — all date filtering/aggregation uses `dim_date`.

## Surrogate vs Natural Key Policy

- **All dimensions**: Surrogate key (`*_sk`) as PK; natural key (`*_id`) as business key with unique constraint
- **All facts**: Surrogate key (`*_sk`) as PK; natural key (`*_id`) as business key with unique constraint
- **Fact FKs**: Always surrogate keys (`*_sk`) referencing dimension surrogates
- **SCD2**: `dim_customer` uses `customer_sk` + `dbt_valid_from`/`dbt_valid_to` + `is_current` for versioning

## Star Schema Diagram

```
                    ┌──────────────┐
                    │  dim_date    │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  fct_orders   │  │ fct_payments  │  │ fct_returns   │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ dim_customer  │  │  dim_product  │  │ fct_order_it. │
│    (SCD2)     │  └───────┬───────┘  └───────┬───────┘
└───────┬───────┘           │                   │
        │                   ▼                   ▼
        ▼            ┌───────────────┐  ┌───────────────┐
┌───────────────┐    │  dim_region   │  │  dim_product  │
│  dim_region   │    └───────────────┘  └───────────────┘
└───────────────┘
```

## Mart Layer (Derived from Star)

| Mart | Base Facts | Key Dimensions | Business Questions |
|------|------------|----------------|---------------------|
| `mart_sales` | `fct_orders` | `dim_date`, `dim_region`, `dim_customer` | BQ-01, BQ-02, BQ-03 |
| `mart_customer_retention` | `fct_orders` | `dim_customer` (SCD2), `dim_date` | BQ-04, BQ-05 |
| `mart_product_performance` | `fct_order_items` | `dim_product`, `dim_date` | BQ-06 |
| `mart_returns` | `fct_returns`, `fct_order_items` | `dim_product`, `dim_date`, `dim_customer` | BQ-07, BQ-08 |
| `mart_inventory` | `fct_order_items`, `raw.inventory_levels` | `dim_product`, `dim_date`, `dim_region` | BQ-09 |

## Query Pattern

All mart queries follow the same pattern:

```sql
SELECT
  d.date,
  r.region_name,
  SUM(f.total_amount_cents) / 100.0 AS revenue
FROM fct_orders f
JOIN dim_date d ON f.order_date_sk = d.date_sk
JOIN dim_customer c ON f.customer_sk = c.customer_sk
JOIN dim_region r ON c.region_sk = r.region_sk
WHERE d.date BETWEEN '2025-01-01' AND '2025-12-31'
GROUP BY 1, 2
```

No raw/staging tables ever referenced directly.