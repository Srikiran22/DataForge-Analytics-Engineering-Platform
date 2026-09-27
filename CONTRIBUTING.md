# Contributing

DataForge is primarily a portfolio and educational project. Contributions should preserve the existing separation between ingestion, transformation, and presentation layers.

## Development setup

Follow the setup instructions in [README.md](README.md).

Before changing code, run the relevant tests. For a full local check:

```bash
pytest tests/
ruff check ingestion dashboards scripts tests
```

For dbt changes:

```bash
WAREHOUSE_PATH=data/warehouse/analytics.duckdb dbt build --profiles-dir dbt --project-dir dbt
```

## Repository conventions

- Keep extraction and loading logic in `ingestion/`.
- Keep analytical transformations in `dbt/`.
- Keep dashboard code focused on presentation and mart consumption.
- Preserve the raw-layer fidelity rules.
- Do not commit `.env` files, credentials, generated warehouse files, or local artifacts.
- Update tests when changing ingestion behavior, data contracts, or model definitions.
- Update the relevant documentation when an architectural decision changes.

## Pull requests

A useful change should include:

- A clear description of the change and its reason.
- Tests or checks that were run.
- Any environment-specific checks that could not be run.

Keep commits focused on one logical change where practical.
