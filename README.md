# DataForge — Analytics Engineering Platform

Local-first batch analytics platform: e-commerce sources → ingestion → raw →
dbt staging/intermediate/marts (star schema, SCD2) → dashboard, orchestrated by
Airflow, gated by data-quality contracts.

**Status:** Phase 2 of 16 in progress (ingestion + raw layer). Architecture,
research, ADRs, business questions, and imperfection design are complete — see
`docs/`.

Key documents:
- `docs/research.md` — verified tool versions (dated)
- `docs/adr/` — architecture decision records
- `docs/business_questions.md` — question registry every table must trace to
- `docs/data_imperfections.md` — injected defects ↔ quality-mechanism map
- `docs/architecture/architecture-sketch.md` — layered flow + contracts

Full README per spec §39 lands in Phase 14.
