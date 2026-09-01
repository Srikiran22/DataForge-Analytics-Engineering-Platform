# fct_order_items

## Purpose
Order line-item fact supporting BQ-06 (product performance), BQ-07 (returns by product), BQ-09 (inventory position via product).

## Grain
One row per order line item.

## Primary Key
- `order_item_sk` (surrogate key, generated via dbt `generate_surrogate_key` on `item_id`)

## Natural Key
- `item_id` (e.g., "I0000001")

## Foreign Keys
- `order_sk` → `fct_orders.order_sk`
- `product_sk` → `dim_product.product_sk`
- `order_date_sk` → `dim_date.date_sk` (via order)
- `customer_sk` → `dim_customer.customer_sk` (via order)

## Important Constraints
- `item_id` unique, not null
- `order_sk` not null
- `product_sk` not null
- `quantity` > 0 (0.1% outliers per I-08 flagged not rejected)
- `unit_price_cents` ≥ 0 (0.1% outliers flagged not rejected)
- `line_amount_cents` = `quantity` * `unit_price_cents`

## Incremental Strategy
**Merge** on `item_id`. Watermark: `updated_at`. Lookback: 7 days.

## Expected Update Frequency
Daily batch. Items are immutable once order is placed (corrections rare, would be new version).

## Column Dictionary

| Column | Type | Description | Nullable? | Source |
|--------|------|-------------|-----------|--------|
| order_item_sk | BIGINT | Surrogate key | No | dbt generated |
| item_id | VARCHAR | Natural key | No | raw.order_items.item_id |
| order_sk | BIGINT | FK to fct_orders | No | Join on order_id |
| product_sk | BIGINT | FK to dim_product | No | Join on product_id |
| order_date_sk | BIGINT | FK to dim_date | No | Via order join |
| quantity | BIGINT | Units ordered | No | raw.order_items.quantity |
| unit_price_cents | BIGINT | Price per unit in cents | No | raw.order_items.unit_price_cents |
| line_amount_cents | BIGINT | quantity * unit_price_cents | No | Computed |
| updated_at | TIMESTAMP | Source watermark | No | raw.order_items.updated_at |

## Measures
- `quantity` (additive)
- `line_amount_cents` (additive)
- `item_count` (count of line items)