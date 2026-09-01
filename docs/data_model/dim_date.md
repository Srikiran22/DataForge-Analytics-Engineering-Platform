# dim_date

## Purpose
Conformed date dimension used by all fact tables for time-based analysis (BQ-01, BQ-02, BQ-04, BQ-05, BQ-06, BQ-07, BQ-08).

## Grain
One row per calendar day.

## Primary Key
- `date_sk` (surrogate key, integer format YYYYMMDD)

## Natural Key
- `date` (DATE)

## Foreign Keys
Referenced by all fact tables via `order_date_sk`, `returned_date_sk`, `payment_date_sk`, `snapshot_date_sk`.

## Important Constraints
- `date` unique, not null
- `date_sk` = `year * 10000 + month * 100 + day`
- Continuous range covering all data dates (2024-09-01 to 2026-08-25 + buffer)
- `is_weekend`, `is_holiday` boolean flags

## Slowly Changing Behavior
**Static** — date dimension is immutable once generated. No updates.

## Expected Update Frequency
Generated once at warehouse initialization. Extended only if data window expands.

## Column Dictionary

| Column | Type | Description | Nullable? | Source |
|--------|------|-------------|-----------|--------|
| date_sk | BIGINT | Surrogate key (YYYYMMDD) | No | Generated |
| date | DATE | Calendar date | No | Generated |
| year | SMALLINT | Year (e.g., 2025) | No | Extracted |
| quarter | SMALLINT | Quarter (1-4) | No | Extracted |
| month | SMALLINT | Month (1-12) | No | Extracted |
| month_name | VARCHAR | Month name | No | Extracted |
| day | SMALLINT | Day of month (1-31) | No | Extracted |
| day_of_week | SMALLINT | Day of week (1=Mon, 7=Sun) | No | Extracted |
| day_name | VARCHAR | Day name | No | Extracted |
| week_of_year | SMALLINT | ISO week | No | Extracted |
| is_weekend | BOOLEAN | Sat/Sun | No | Computed |
| is_holiday | BOOLEAN | Major holiday (US) | No | Computed |
| fiscal_year | SMALLINT | Fiscal year (Oct-Sep) | No | Computed |
| fiscal_quarter | SMALLINT | Fiscal quarter | No | Computed |

## Coverage
Generated for 2024-01-01 through 2027-12-31 (covers full data window + buffer).