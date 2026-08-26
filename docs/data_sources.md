# Data Source Catalog

**Status: Phase 1 design.** Row counts below are **targets** for the seed generator — actual achieved numbers get recorded in Phase 2 when `make seed` first runs (spec rule: state real numbers, never aspirational ones presented as facts).

## Source systems (4 required shapes — spec §3.1)

| # | Source | Shape | Transport/format | Grain of records | Watermark field (preview; full decision in Phase 2) |
|---|---|---|---|---|---|
| S1 | `customers` | CSV file | `data/source/customers.csv`, header + rows | 1 row per customer | append-only file + `_source_file` tracking |
| S2 | `regions` | CSV file | `data/source/regions.csv`, small static reference | 1 row per region | full reload each run (tiny) |
| S3 | `orders` | JSON (NDJSON) | `data/source/orders.json`, one JSON object per line | 1 line per order (header) | `updated_at` high-water mark |
| S4 | `returns` | JSON (NDJSON) | `data/source/returns.json`, event-style | 1 line per return event | `returned_at` high-water mark |
| S5 | `products` | REST API (mocked) | FastAPI service in Compose serving `/products` from versioned fixture files | 1 record per product per API version | full snapshot per pull + version tag |
| S6 | OLTP: `order_items`, `payments`, `inventory_levels` | Relational DB | PostgreSQL 17 container, schema `source_oltp` (simulated transactional store) | 1 row per order line / payment / stock position | `updated_at` columns |

## API mock decision (required documentation — spec §3.1 "document which")

**Chosen: FastAPI**, serving fixture files under `data/fixtures/products/v1.json`, `v2.json`.

Why FastAPI over Flask:
- Pydantic response models give us a *typed* API surface — the v1→v2 schema-drift exercise (new column added mid-stream, spec §23) is then a realistic contract change on the producer side, not just a file swap.
- Async endpoint + uvicorn is one small container (~tens of MB RSS), inside our RAM envelope.
- Flask would serve equally well functionally; no capability gap either way — recorded so the choice is visibly low-stakes.

The mock also supports simulating failure modes needed by §20 reliability tests: `/products?fail=500` returns errors so source-unavailable behavior can be induced deliberately.

## Volume targets (to be replaced with measured actuals in Phase 2)

> Superseded by the measured-actuals table below — kept for traceability of what was planned vs achieved.

| Dataset | Target rows | Rationale |
|---|---|---|
| customers | ~40,000 | enough for SCD2 history to be non-trivial across 24 months |
| regions | ~12 | static reference |
| products | ~8,000 | enough for ranking/performance spread |
| orders | ~250,000 | daily batch realism over 24 months (~340/day avg) |
| order_items | ~450,000 | 1.8 items/order average |
| payments | ~260,000 | ≥1 payment per order incl. splits/refund events |
| returns | ~18,000 | ~4% of items returned → meaningful but minority class |
| inventory_levels | ~8,000 current positions (+ optional weekly snapshot history) | serves BQ-09 |

Total ≈ 1M rows — inside "tens of thousands to low millions" (§3.3), large enough that incremental-vs-full-refresh timing differences are measurable on limited hardware.

## Seed reproducibility commitments

- Single fixed RNG seed, defined in one config file (`configs/seed.yaml` in Phase 2), checked into the repo.
- `make seed` must be byte-identical across runs on the same machine and stable across machines for the same tool versions.
- Imperfections are injected **by the same seeded generator** (flags per `docs/data_imperfections.md`) — never by hand-editing output files.

## Measured actuals (Phase 2, 2026-08-26)

From data/seed/seed_summary.json + scripts/report_raw_evidence.py against the current generator (rng_seed 20260826):

| Dataset | Actual generated | Actual loaded to raw | Difference explained |
|---|---|---|---|
| customers | 40,000 | 40,000 | snapshot-replace semantics |
| regions | 12 | 12 | - |
| orders (file lines incl. replays + corrupt) | 248,832+1,738 = 250,570 window total; 247,490 in prior build | 248,832 | malformed (523) quarantined at parse; invalid FK (1,215) quarantined at integrity gate |
| order_items (OLTP CSV) | 554,709 | pending Docker | RDBMS shape test blocked on source Postgres |
| payments (OLTP CSV) | 245,399 | pending Docker | same |
| returns | 13,435 file lines | 13,435 loaded +23 quarantined | - |
| inventory_levels (OLTP CSV) | 8,000 | pending Docker | same |

Generation time: ~14-17s per full run. Regeneration byte-identical (MD5 verified on two files across runs).
