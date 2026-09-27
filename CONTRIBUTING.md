# Contributing

DataForge is primarily a portfolio and educational project. Contributions are welcome when they improve correctness, reproducibility, documentation, or maintainability.

## Before making changes

- Read the architecture documentation in `docs/architecture/`.
- Check the relevant ADRs in `docs/adr/`.
- Run the existing test suite before changing behavior.
- Keep raw-layer, dbt, and dashboard responsibilities separate.

## Development checks

Run:

```bash
pytest tests/
```

For dbt changes:

```bash
WAREHOUSE_PATH=data/warehouse/analytics.duckdb dbt build
```

For linting:

```bash
ruff check .
```

## Pull requests

A useful pull request should explain:

1. What changed.
2. Why the change was needed.
3. Which tests were run.
4. Any environment-dependent checks that could not be run.

Avoid changing generated data, local warehouse files, credentials, or environment-specific configuration in commits.
