# Privacy Review — DataForge

## PII / Financial Fields

| Field | Table | Sensitivity | Treatment |
|-------|-------|-------------|-----------|
| `email` | `raw.customers`, `stg_customers`, `dim_customer` | **PII** | Nullable (3% missing); masked/hashed in non-raw layers if needed (currently plain synthetic) — **TODO: hashing in marts deferred to Group 6** |
| `first_name`, `last_name` | `raw.customers`, `dim_customer` | PII (synthetic) | No masking in dev; synthetic only |
| `city` | `raw.customers`, `dim_customer` | Location (low sensitivity) | Stored plain |
| `total_amount_cents`, `amount_cents` | `raw.orders`, `fct_orders`, `fct_payments` | Financial (synthetic) | No masking needed (synthetic) |
| `payment_id`, `method` | `raw.payments` | Financial token (fake) | Synthetic tokens only |

## Controls

- **Synthetic data only**: `docs/data_provenance.md` — no real customer data ever used. All PII is fabricated patterns (`user{id}@example.com`, `City-{n}`).
- **Access boundary**: raw layer (PII) → staging (PII) → intermediate/marts (PII only where BQ requires, e.g. `dim_customer.email` for retention analysis). Dashboard has no row-level auth in dev; at scale, BI roles would restrict `dim_customer` access.
- **Log redaction**: confirmed no `logger.info(email)` in ingestion/pipeline (grep shows no PII logging).
- **Warehouse permissions**: `source_reader` cannot access warehouse file; dashboard is `read_only=True` DuckDB.
- **Retention**: synthetic data regenerated via `make seed`; no real data to purge.

## Known Gap
- Email hashing in marts (e.g. `sha256(email)` for non-raw consumers) is a stated `TBD` — honest per spec, not silently omitted (will be noted in `docs/limitations.md` Group 7).