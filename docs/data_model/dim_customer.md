# dim_customer

## Purpose
Customer dimension supporting BQ-02 (repeat purchase rate), BQ-04 (cohort retention), and BQ-05 (cohort analysis).

## Grain
One row per customer version (SCD Type 2). A new version is created when any tracked attribute changes.

## Primary Key
- `customer_sk` (surrogate key, generated via dbt `generate_surrogate_key` on `customer_id` + `dbt_valid_from`)

## Natural Key
- `customer_id` (e.g., "C000001")

## Foreign Keys
- `region_sk` → `dim_region.region_sk`

## Important Constraints
- `customer_id` not null
- `customer_sk` unique, not null
- `dbt_valid_from` not null
- `is_current` boolean, not null
- `email` nullable (3% missing per I-01)
- `is_current = true` for exactly one row per `customer_id`

## Slowly Changing Behavior
**Type 2 (SCD2)** — tracked columns: `email`, `city`, `region_id`, `segment`. When any change, previous row gets `dbt_valid_to` = change timestamp, `is_current = false`, new row inserted with `dbt_valid_from` = change timestamp, `is_current = true`.

Tracked attributes: `email`, `city`, `region_id`, `segment`.
Non-tracked (Type 1): `first_name`, `last_name` (corrections overwrite in place).

## Expected Update Frequency
Daily batch. Customer attributes change infrequently (~2-3% per month in synthetic data).

## Column Dictionary

| Column | Type | Description | Nullable? | Source |
|--------|------|-------------|-----------|--------|
| customer_sk | BIGINT | Surrogate key | No | dbt generated |
| customer_id | VARCHAR | Natural key (e.g., "C000001") | No | raw.customers.customer_id |
| first_name | VARCHAR | Given name | No | raw.customers.first_name |
| last_name | VARCHAR | Family name | No | raw.customers.last_name |
| email | VARCHAR | Email address | Yes (3% null) | raw.customers.email |
| city | VARCHAR | City of residence | No | raw.customers.city |
| region_id | VARCHAR | Region code (FK to dim_region) | No | raw.customers.region_id |
| segment | VARCHAR | Customer segment (consumer/corporate) | No | raw.customers.segment |
| signup_date | DATE | Account creation date | No | raw.customers.signup_date |
| dbt_valid_from | TIMESTAMP | Row validity start | No | dbt snapshot |
| dbt_valid_to | TIMESTAMP | Row validity end (null = current) | Yes | dbt snapshot |
| is_current | BOOLEAN | Current version flag | No | dbt snapshot |

## SCD2 Test Scenarios (Phase 5 verification)
1. Customer changes city → old row `is_current=false`, `dbt_valid_to` set; new row `is_current=true`
2. Customer changes region and segment in same batch → exactly one new version row
3. Order before address change joins to dimension version valid at order time
4. Re-running snapshot on unchanged data produces zero new rows