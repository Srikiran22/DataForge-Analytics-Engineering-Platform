# dim_region

## Purpose
Conformed region dimension referenced by dim_customer and used for regional rollups in BQ-01 (monthly revenue by region) and BQ-02 (AOV by region).

## Grain
One row per region.

## Primary Key
- `region_sk` (surrogate key, generated via dbt `generate_surrogate_key` on `region_id`)

## Natural Key
- `region_id` (e.g., "RG01")

## Foreign Keys
Referenced by `dim_customer.region_sk`.

## Important Constraints
- `region_id` unique, not null
- `region_sk` unique, not null
- `country` not null

## Slowly Changing Behavior
**Type 1** — region attributes are stable. Corrections overwrite in place.

## Expected Update Frequency
Static reference data (12 rows). Reloaded full each batch but no changes expected.

## Column Dictionary

| Column | Type | Description | Nullable? | Source |
|--------|------|-------------|-----------|--------|
| region_sk | BIGINT | Surrogate key | No | dbt generated |
| region_id | VARCHAR | Natural key (e.g., "RG01") | No | raw.regions.region_id |
| region_name | VARCHAR | Display name (e.g., "Region-01") | No | raw.regions.region_name |
| country | VARCHAR | ISO country code | No | raw.regions.country |

## Coverage
12 regions spanning US, CA, BR, DE, FR, GB, IN, JP, AU, ZA, MX.