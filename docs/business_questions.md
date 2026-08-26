# Business Question Registry

**Status: authoritative for Phase 1.** Written BEFORE any table, schema, mart, or transformation exists (spec §2.1). Every fact/dimension/mart built in later phases must trace back to a row here; any table that cannot be traced gets deleted or this registry gets fixed — no third option.

Domain: **e-commerce** (per spec §2 default; no Phase 0 finding justified deviation).

## Registry

| ID | Question | Owning mart | Key metric(s) | Refresh cadence needed |
|---|---|---|---|---|
| BQ-01 | What is the monthly revenue trend by region? | `mart_sales` | net_revenue, gross_revenue (by month × region) | daily |
| BQ-02 | What is our overall and per-region average order value, and how does it trend over time? | `mart_sales` | avg_order_value (by month × region) | daily |
| BQ-03 | How many orders do we process, split by status (placed/shipped/delivered/cancelled)? | `mart_sales` | order_count, order_status distribution | daily |
| BQ-04 | What % of customers are repeat purchasers? | `mart_customer_retention` | repeat_purchase_rate | daily |
| BQ-05 | How do customer cohorts (first-purchase month) retain and spend over subsequent months? | `mart_customer_retention` | cohort_size, retained_customers, cohort_revenue by months_since_first_purchase | daily |
| BQ-06 | Which products drive revenue and units sold, and how is that shifting? | `mart_product_performance` | product_revenue, units_sold, revenue_rank (with month-over-month movement) | daily |
| BQ-07 | What are return rates by product and category, and why do customers return items? | `mart_returns` | return_rate, returned_units, return_reason distribution | daily |
| BQ-08 | What is the financial impact of returns on net revenue? | `mart_returns` + `mart_sales` | returned_value, net_of_returns revenue | daily |
| BQ-09 | What is our current inventory position per product/warehouse, and which items are low or out of stock? | `mart_inventory` | stock_on_hand, days_of_cover, low_stock_flag | daily |

## Coverage check against spec §2.2 minimums

| Required area | Covered by |
|---|---|
| Revenue | BQ-01, BQ-08 |
| Orders | BQ-03 |
| Average order value | BQ-02 |
| Customer retention / repeat purchases | BQ-04, BQ-05 |
| Product performance | BQ-06 |
| Regional performance | BQ-01, BQ-02 (region grain) |
| Returns | BQ-07, BQ-08 |
| Inventory position | BQ-09 |
| Customer cohorts | BQ-05 |

All nine minimum areas covered. No padding questions added.

## Deliberate exclusions (recorded so their absence is a decision, not an oversight)

- **Customer lifetime value (CLV)**: excluded from the registry at Phase 1. A defensible CLV needs assumptions about repeat-purchase cadence/horizon that our 24-month synthetic window can ground only descriptively. Per spec §26 it may only exist "if you can justify the assumptions" — decision deferred to the metrics-dictionary phase with explicit justification or explicit rejection there.
- Marketing attribution, sessions/web traffic, shipping/logistics cost metrics: no source system for them exists in §3 scope; inventing one would violate "no fake enterprise-ness."

## Downward traceability contract

Later-phase artifacts must reference these IDs:

| Artifact | Rule |
|---|---|
| Every dimension/fact table doc (`docs/data_model/<table>.md`, Phase 3) | Purpose line cites ≥1 BQ ID |
| Every mart's `schema.yml` description (Phase 4) | cites its BQ ID(s) |
| Every metrics-dictionary entry (`docs/metrics_dictionary.md`) | lists the BQ ID(s) it serves |
| Dashboard panels (Phase 9) | panel title maps to a BQ ID |

A question with no table = gap to fix in Phase 3. A table with no question = delete it.
