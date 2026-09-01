# dim_product

## Purpose
Product dimension supporting BQ-06 (product performance by revenue/units) and BQ-07 (returns by product/category).

## Grain
One row per product (Type 1 — attributes overwritten on change). Products are relatively stable; category/casing changes are normalized in staging.

## Primary Key
- `product_sk` (surrogate key, generated via dbt `generate_surrogate_key` on `product_id`)

## Natural Key
- `product_id` (e.g., "P000001")

## Foreign Keys
None directly. Referenced by `fct_order_items.product_sk`.

## Important Constraints
- `product_id` unique, not null
- `product_sk` unique, not null
- `category` normalized to lower case (per I-07)
- `price_cents` > 0 (except 0.1% outliers per I-08, flagged not rejected)
- `brand` nullable (added in schema drift v2 per I-05)

## Slowly Changing Behavior
**Type 1** — attributes overwritten on change. Product catalog changes are rare; corrections to name/category/price overwrite in place. Brand column added via schema drift (I-05) — new column appears, handled by contract "warn + adapt".

## Expected Update Frequency
Daily batch (full snapshot from API). API v2 serves `brand` column from 2026-02-01 onward (I-05).

## Column Dictionary

| Column | Type | Description | Nullable? | Source |
|--------|------|-------------|-----------|--------|
| product_sk | BIGINT | Surrogate key | No | dbt generated |
| product_id | VARCHAR | Natural key (e.g., "P000001") | No | raw.products.product_id |
| name | VARCHAR | Product name | No | raw.products.name |
| category | VARCHAR | Normalized category (lower case) | No | raw.products.category (staged) |
| price_cents | BIGINT | Price in cents | No | raw.products.price_cents |
| active | BOOLEAN | Currently sold | No | raw.products.active |
| brand | VARCHAR | Brand name (added in v2) | Yes | raw.products.brand (v2 only) |

## Schema Drift Handling (I-05)
- v1 API (before 2026-02-01): no `brand` column
- v2 API (2026-02-01 onward): `brand` column present
- Contract policy: warn + adapt — extra column ignored unless mapped
- dbt model handles missing `brand` gracefully (defaults to NULL for v1 records)