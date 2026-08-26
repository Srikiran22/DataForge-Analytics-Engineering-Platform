# Watermark Strategy (spec §9.1)

## Per-source watermark decision

| Source | Shape | Watermark field | Strategy | Why |
|---|---|---|---|---|
| orders | NDJSON daily files | `updated_at` | high-water mark | order records mutate (status transitions); `updated_at` advances on change per source contract |
| returns | NDJSON daily files | `returned_at` (aliased into `updated_at`) | high-water mark | append-only event stream; event time is the natural ordering key |
| order_items / payments / inventory_levels | RDBMS | `updated_at` | high-water mark | classic CDC-lite pattern against an OLTP table we control |
| customers | CSV | none | full snapshot replace | file is a wholesale export; no reliable mutation timestamp on removed rows |
| regions | CSV | none | full snapshot replace | tiny static reference |
| products | REST API | none (version tag in fixture header) | full snapshot per pull | API exposes no delta endpoint at this scale |

## Why `updated_at` high-water mark for transactional sources

- Chosen over monotonically-increasing batch ID because our NDJSON/RDBMS sources mutate individual records; a pure batch-ID cursor cannot express "re-fetch changed rows".
- Known risk accepted and mitigated: **clock skew / out-of-order timestamps**. Mitigations: (a) watermark advances only to the max value actually observed and committed (`advance_if_newer`, strictly monotonic guard); (b) late-arriving rows are caught by the incremental **lookback window** in the dbt layer (assumed max lateness = **7 days**, matching the generator's late-payment injection; documented again in §21/§22 work).
- Gaps risk (batch-ID approach) does not apply; duplicate-delivery risk is handled instead: records arriving with `updated_at ≤ watermark` are counted (`skipped_replayed`) and skipped — they are byte-identical redeliveries by definition of the source contract ("`updated_at` MUST advance on any mutation").

## Persistence and failure semantics

State lives in DuckDB:

```
raw.ingestion_watermarks(source_name PK, watermark_field, watermark_value, advanced_at, last_batch_id)
```

- Advance happens **only after** the corresponding batch transaction has committed (`pipeline.run_source`: extract → gate → load(commit) → lineage → advance).
- A failed batch therefore never moves the watermark; recovery re-extracts the same window. Proven empirically by `tests/integration/test_failure_semantics.py::test_failed_load_does_not_advance_watermark_even_with_prior_state`.
- Watermarks are part of recoverable state: deleting the warehouse file and re-running `init-warehouse` + loads reproduces them deterministically from source data (no hidden state outside the warehouse).

## Batch identity

`batch_id = <UTC timestamp>-<8 hex random>` generated per run, overridable via CLI `--batch-id`. Replace-by-batch-id gives rerun safety; snapshot-shaped sources additionally replace the whole table on success (see `docs/architecture/raw_layer.md`).
