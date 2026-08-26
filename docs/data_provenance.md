# Data Provenance Statement

## Synthetic-data declaration

All data in this platform is **synthetically generated** by this repository's own seeded generator. No real, private, or licensed dataset is copied, derived, or embedded anywhere in the repo.

- No real customer PII exists at any point — names, emails, addresses are fabricated patterns (this doubles as the synthetic-data control referenced by `docs/privacy_review.md`, Phase 11).
- Payment identifiers are fake tokens in obvious test formats.

## Realism pattern

The domain model (customers place orders composed of items; payments settle orders; returns reference items; inventory tracks stock positions) follows **generic e-commerce conventions** common to retail analytics schemas. It was not patterned after any single named public dataset; no public dataset was downloaded or inspected during design.

Rationale: pattern-matching a specific public dataset (e.g., an open e-commerce order dump) would import its licensing constraints (many Kaggle datasets are non-commercial CC variants) for zero functional benefit — our quality-layer requirements come from `docs/data_imperfections.md`, not from any external schema's quirks.

## Reproducibility

- Generator seed: fixed value in `configs/seed.yaml` (introduced Phase 2), committed.
- Same seed + same generator code + pinned tool versions ⇒ identical outputs.
- If realism parameters change (volumes, distributions), the change is a reviewed commit so any historical benchmark number stays attributable to a known data state.
