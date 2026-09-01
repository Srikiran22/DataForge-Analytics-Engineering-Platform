# fct_returns

## Purpose
Returns fact supporting BQ-07 (return rates by product/category) and BQ-08 (financial impact of returns).

## Grain
One row per return event.

## Primary Key
- `return_sk` (surrogate key, generated via dbt `generate_surrogate_key` on `return_id`)

## Natural Key
- `return_id` (e.g., "R000001")

## Foreign Keys
- `order_item_sk` → `fct_order_items.order_item_sk`
- `return_date_sk` → `dim_date.date_sk`
- `product_sk` → `dim_product.product_sk` (via order_item)
- `customer_sk` → `dim_customer.customer_sk` (via order)

## Important Constraints
- `return_id` unique, not null
- `order_item_sk` not null
- `return_date_sk` not null
- `reason` ∈ ['wrong_item', 'damaged', 'not_as_described', 'better_price', 'changed_mind']
- `quantity` > 0
- `returned_at` ≥ order_ts (validated in staging)

## Incremental Strategy
**Merge** on `return_id`. Watermark: `returned_at` (aliased as `updated_at` in raw). Lookback: 7 days.

## Expected Update Frequency
Daily batch. Returns are immutable once recorded.

## Column Dictionary

| Column | Type | Description | Nullable? | Source |
|--------|------|-------------|-----------|--------|
| return_sk | BIGINT | Surrogate key | No | dbt generated |
| return_id | VARCHAR | Natural key | No | raw.returns.return_id |
| order_item_sk | BIGINT | FK to fct_order_items | No | Join on order_item_id |
| return_date_sk | BIGINT | FK to dim_date | No | raw.returns.returned_at |
| reason | VARCHAR | Return reason | No | raw.returns.reason |
| quantity | BIGINT | Units returned | No | raw.returns.quantity |
| returned_at | TIMESTAMP | Return timestamp | No | raw.returns.returned_at |
| updated_at | TIMESTAMP | Source watermark | No | raw.returns.updated_at |

## Measures
- `quantity` (additive)
- `return_count` (count of returns)

## Malformed Handling (I-04)
- ~0.2% malformed JSON lines quarantined at ingestion
- Valid returns loaded, malformed counted in quarantine