# Raw Layer Design (spec §10)

## Why this layer exists

The raw layer duplicates information that staging will re-type and clean. It earns its disk space four ways:

1. **Replayability** — transformations can be rebuilt from raw without re-touching source systems (which may be unavailable or mutated).
2. **Debugging** — when staging/mart numbers look wrong, raw is the ground truth boundary between ingestion bugs and transformation bugs.
3. **Audit trail** — every row carries provenance metadata; any mart figure can be traced back to a specific batch.
4. **Decoupling** — ingestion cadence (per-file, per-pull) is independent of transformation cadence (dbt build).

## Fidelity policy

- Raw payload columns are **all VARCHAR**: values are stored exactly as delivered, never cast at the boundary. A malformed numeric cannot be silently dropped or coerced — it lands in raw verbatim and any type problem surfaces (and fails loudly) in staging.
- **Duplicates are preserved.** Exact replays never reach raw (watermarked skip, counted as `skipped_replayed`), but mutated re-deliveries land as additional versions (`order_id O0122469` ×2 in the current warehouse). Choosing the current version is a *staging* business rule, not an ingestion side effect.
- **Quarantine, not deletion.** Unparseable lines and referentially-invalid records go to `raw.quarantine_<source>` with `reason`, `error_detail`, and the offending payload attached. Nothing is dropped silently.

## Ingestion metadata columns (every raw table)

| Column | Meaning |
|---|---|
| `_source_name` | source key from `ingestion/sources.py` |
| `_batch_id` | batch identity; same id re-run replaces its own rows |
| `_ingested_at` | UTC timestamp of the load call |
| `_source_file` | shape:path reference (e.g. `ndjson:orders`) |
| `_source_row_number` | original line/row position within the batch |

## Snapshot vs incremental sources

| Type | Sources | Successful-load semantics |
|---|---|---|
| Snapshot (no watermark field) | customers, regions, products | new batch **replaces entire table** — repeated exports never accumulate stale copies (bug found and fixed in Phase 2; see audit note below) |
| Incremental (watermark field) | orders, returns, order_items, payments, inventory_levels | batches accumulate; watermark gates extraction |

Phase 2 defect log (found via evidence pass, fixed, re-proven):
1. Zero-record reruns deleted prior committed batch rows → loader now no-ops when nothing extracted (caught by `test_duplicate_batch_submission_never_duplicates_data`).
2. Snapshot sources accumulated 80k customer rows across runs → `replace_all` semantics added (caught by `test_new_full_export_replaces_stale_snapshot_not_accumulates`).
3. Generator's percentage rounding injected ~zero malformed lines → Bernoulli injection counts (caught during evidence collection: quarantine was empty).

## Bulk-load mechanics

Batches serialize to temp newline-delimited JSON and insert via DuckDB `read_json` inside one explicit transaction. Rationale: row-wise `executemany` measured ~160s for 40k rows; bulk path measures ~1s. This doubles as the §29 optimization case study (before/after recorded in `docs/performance_benchmarks.md` in Phase 12).

## Current measured state (2026-08-26, post-fix rebuild)

See `scripts/report_raw_evidence.py` output in the Phase 2 gate report — raw counts, quarantine breakdown by reason, watermarks, and lineage rows are all queryable from the warehouse itself rather than asserted here.
