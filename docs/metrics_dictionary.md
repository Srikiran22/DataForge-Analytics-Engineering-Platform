# Metrics Dictionary — Single Source of Truth (spec §26)

Every metric is defined in exactly one intermediate model/macro and consumed by every mart/panel without re-derivation.

## Gross Revenue
- Definition: Sum of `total_amount_cents` for orders with `status` in ('delivered','shipped') per calendar day/region, converted to dollars.
- Grain: 1 row per (date, region) in `mart_sales`
- SQL: `dbt/models/marts/sales/mart_sales.sql` → `total_amount_cents / 100.0`
- Source tables: `fct_orders`
- Tests: `not_null` on `gross_revenue`; business-rule `net_revenue <= gross_revenue` (singular test)
- Limitation: excludes cancelled/returned at gross; net adjusts via `returned_revenue`.

## Net Revenue
- Definition: `gross_revenue - returned_revenue` (returned value from `fct_returns` via `fct_order_items`).
- Grain: 1 row per (date, region)
- SQL: same mart ` (total_amount_cents - coalesce(returned_amount_cents,0))/100.0`
- Source tables: `fct_orders`, `fct_returns`
- Tests: `assert_net_le_gross` (singular)

## Order Count
- Definition: Count of distinct `order_id` where status in ('delivered','shipped','placed').
- Grain: per day × region in `mart_sales` (aggregated)
- SQL: `count(distinct order_id)` in `mart_sales` base CTE
- Source tables: `fct_orders`
- Tests: `unique` on `order_sk`, `not_null` on `order_id`

## Average Order Value (AOV)
- Definition: `net_revenue / order_count` per period.
- Grain: derived at query time from `mart_sales` (never materialized separately to avoid drift).
- SQL: `avg(net_revenue / nullif(order_count,0))` — computed in dashboard, sourced from `mart_sales`
- Tests: same as order count + net revenue

## Repeat Purchase Rate
- Definition: Fraction of customers with >1 order / total customers, per cohort window.
- Grain: per `cohort_month` in `mart_customer_retention`
- SQL: `dbt/models/marts/customer_retention/mart_customer_retention.sql` → cohort CTEs
- Source tables: `fct_orders`, `dim_customer` (SCD2)
- Tests: relationships on `customer_sk`

## Cohort Retention
- Definition: For customers whose first order falls in month M, fraction still ordering in month M+N and revenue in M+N.
- Grain: 1 row per (cohort_month, order_month)
- SQL: same retention mart `retention_rate` column
- Source tables: `fct_orders` + `dim_customer`
- Known limitation: window limited to synthetic 24 months.

## Product Revenue / Units Sold / Return Rate
- Definition: `sum(line_amount_cents)/100` and `sum(quantity)` per product from `fct_order_items`; return rate = `returned_units / units_sold`.
- Grain: 1 row per `product_sk` in `mart_product_performance`
- SQL: `mart_product_performance.sql`
- Source tables: `fct_order_items`, `dim_product`
- Tests: `not_null` on `product_revenue`, `units_sold` + `accepted_values` on category

## Return Rate (overall)
- Definition: `sum(returned_quantity) / sum(ordered_quantity)` per category/reason/date.
- Grain: per (date, category, reason) in `mart_returns`
- SQL: `mart_returns.sql`
- Source tables: `fct_returns`, `fct_order_items`
- Tests: `accepted_values` on `reason`

## Inventory Position
- Definition: `stock_on_hand` snapshot per (product, warehouse); `days_of_cover = floor(stock_on_hand / avg_daily_units_sold)` (30d velocity); `low_stock_flag = stock_on_hand <= reorder_point`.
- Grain: 1 row per (product, warehouse)
- SQL: `mart_inventory.sql`
- Source tables: `stg_inventory_levels`, `fct_order_items`
- Tests: `not_null` on `stock_on_hand`, `accepted_values` on `low_stock_flag`
- Limitation: `days_of_cover` null when velocity = 0 (no sales in last 30d) — 816 such rows in current data; panel treats null as "N/A".

## Freshness (operational, not business)
- Definition: `max(_ingested_at)` per `source_name` and `watermark_value` from `raw.ingestion_watermarks` / `lineage.batch_lineage`, rendered via `obs_pipeline_runs`.
- Grain: 1 row per source
- SQL: `dbt/models/observability/obs_pipeline_runs.sql`
- Source tables: `raw.*`, `lineage.batch_lineage`
- Panel: staleness flag when `now - last_ingested_at > 26h` (matches source freshness warn threshold).