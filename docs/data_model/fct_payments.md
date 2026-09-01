# fct_payments

## Purpose
Payment fact supporting BQ-08 (financial impact of returns on net revenue) and reconciliation of payment status.

## Grain
One row per payment event.

## Primary Key
- `payment_sk` (surrogate key, generated via dbt `generate_surrogate_key` on `payment_id`)

## Natural Key
- `payment_id` (e.g., "PM000001")

## Foreign Keys
- `order_sk` → `fct_orders.order_sk`
- `payment_date_sk` → `dim_date.date_sk` (payment event_ts)
- `customer_sk` → `dim_customer.customer_sk` (via order)

## Important Constraints
- `payment_id` unique, not null
- `order_sk` not null
- `payment_date_sk` not null
- `status` ∈ ['pending', 'settled', 'failed', 'refunded']
- `amount_cents` ≥ 0
- `method` ∈ ['card', 'paypal', 'bank_transfer']
- `event_ts` ≤ `updated_at` (event timestamp backdated for late arrivals per I-06)

## Incremental Strategy
**Merge** on `payment_id`. Watermark: `updated_at`. Lookback: 7 days (covers late-arriving payments per I-06).

## Expected Update Frequency
Daily batch. Payments arrive late (I-06: 2% backdated). Status transitions: pending→settled, settled→refunded.

## Column Dictionary

| Column | Type | Description | Nullable? | Source |
|--------|------|-------------|-----------|--------|
| payment_sk | BIGINT | Surrogate key | No | dbt generated |
| payment_id | VARCHAR | Natural key | No | raw.payments.payment_id |
| order_sk | BIGINT | FK to fct_orders | No | Join on order_id |
| payment_date_sk | BIGINT | FK to dim_date (event_ts) | No | raw.payments.event_ts |
| amount_cents | BIGINT | Payment amount in cents | No | raw.payments.amount_cents |
| status | VARCHAR | Payment status | No | raw.payments.status |
| method | VARCHAR | Payment method | No | raw.payments.method |
| event_ts | TIMESTAMP | Payment event time | No | raw.payments.event_ts |
| updated_at | TIMESTAMP | Source watermark | No | raw.payments.updated_at |

## Measures
- `amount_cents` (additive)
- `payment_count` (count of payments)

## Late-Arrival Handling (I-06)
- 2% of payments have `event_ts` near order date but `updated_at` days later
- Incremental lookback (7 days) captures late arrivals
- Reconciliation test: payment totals match regardless of arrival order