# fct_orders

## Purpose
Order header fact supporting BQ-01 (monthly revenue by region), BQ-02 (AOV), BQ-03 (order count by status).

## Grain
One row per order.

## Primary Key
- `order_sk` (surrogate key, generated via dbt `generate_surrogate_key` on `order_id`)

## Natural Key
- `order_id` (e.g., "O000001")

## Foreign Keys
- `customer_sk` → `dim_customer.customer_sk`
- `order_date_sk` → `dim_date.date_sk`
- `region_sk` → `dim_region.region_sk` (via customer)

## Important Constraints
- `order_id` unique, not null
- `order_sk` unique, not null
- `customer_sk` not null (referential integrity)
- `order_date_sk` not null
- `status` ∈ ['placed', 'shipped', 'delivered', 'cancelled', 'returned']
- `total_amount_cents` ≥ 0 (0.1% outliers per I-08 flagged not rejected)
- `currency` = 'USD'

## Incremental Strategy
**Merge** on `order_id` (natural key). Watermark: `updated_at`. Lookback window: 7 days (covers late-arriving payments per I-06, max assumed lateness).

## Expected Update Frequency
Daily batch. Orders mutate through status transitions (placed→shipped→delivered). Incremental merge captures status updates.

## Column Dictionary

| Column | Type | Description | Nullable? | Source |
|--------|------|-------------|-----------|--------|
| order_sk | BIGINT | Surrogate key | No | dbt generated |
| order_id | VARCHAR | Natural key | No | raw.orders.order_id |
| customer_sk | BIGINT | FK to dim_customer | No | SCD2 join on customer_id at order_ts |
| order_date_sk | BIGINT | FK to dim_date (order_ts) | No | raw.orders.order_ts |
| status | VARCHAR | Order status | No | raw.orders.status |
| total_amount_cents | BIGINT | Order total in cents | No | raw.orders.total_amount_cents |
| currency | VARCHAR | ISO currency code | No | raw.orders.currency |
| order_ts | TIMESTAMP | Order timestamp | No | raw.orders.order_ts |
| updated_at | TIMESTAMP | Source watermark | No | raw.orders.updated_at |

## Measures
- `total_amount_cents` (additive)
- `order_count` (count of orders)

## Duplicate Handling (I-02)
- Exact replays (same `updated_at`) skipped by watermark, counted as `skipped_replayed`
- Mutated re-deliveries (advanced `updated_at`) land as second version; staging dedups via `ROW_NUMBER()` keeping max `updated_at`