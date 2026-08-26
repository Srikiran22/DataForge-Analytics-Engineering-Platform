import datetime as dt
import os
import uuid
from pathlib import Path

import duckdb

from ingestion import lineage, quarantine, watermarks
from ingestion.config import env, project_root, warehouse_path
from ingestion.extractors import api as api_extractor
from ingestion.extractors import csv_file, ndjson_file, rdbms
from ingestion.loaders import duckdb_loader
from ingestion.sources import SOURCES

PAYLOAD_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "customers": [
        ("customer_id", "VARCHAR"), ("first_name", "VARCHAR"), ("last_name", "VARCHAR"),
        ("email", "VARCHAR"), ("city", "VARCHAR"), ("region_id", "VARCHAR"),
        ("segment", "VARCHAR"), ("signup_date", "VARCHAR"), ("updated_at", "VARCHAR"),
    ],
    "regions": [("region_id", "VARCHAR"), ("region_name", "VARCHAR"), ("country", "VARCHAR")],
    "orders": [
        ("order_id", "VARCHAR"), ("customer_id", "VARCHAR"), ("order_ts", "VARCHAR"),
        ("status", "VARCHAR"), ("total_amount_cents", "VARCHAR"), ("currency", "VARCHAR"),
        ("updated_at", "VARCHAR"),
    ],
    "returns": [
        ("return_id", "VARCHAR"), ("order_item_id", "VARCHAR"), ("returned_at", "VARCHAR"),
        ("reason", "VARCHAR"), ("quantity", "VARCHAR"), ("updated_at", "VARCHAR"),
    ],
    "products": [
        ("product_id", "VARCHAR"), ("name", "VARCHAR"), ("category", "VARCHAR"),
        ("price_cents", "VARCHAR"), ("active", "VARCHAR"), ("brand", "VARCHAR"),
    ],
    "order_items": [
        ("item_id", "VARCHAR"), ("order_id", "VARCHAR"), ("product_id", "VARCHAR"),
        ("quantity", "VARCHAR"), ("unit_price_cents", "VARCHAR"), ("updated_at", "VARCHAR"),
    ],
    "payments": [
        ("payment_id", "VARCHAR"), ("order_id", "VARCHAR"), ("amount_cents", "VARCHAR"),
        ("status", "VARCHAR"), ("method", "VARCHAR"), ("event_ts", "VARCHAR"),
        ("updated_at", "VARCHAR"),
    ],
    "inventory_levels": [
        ("product_id", "VARCHAR"), ("warehouse_id", "VARCHAR"), ("stock_on_hand", "VARCHAR"),
        ("reorder_point", "VARCHAR"), ("updated_at", "VARCHAR"),
    ],
}


def new_batch_id() -> str:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def connect_warehouse(path: Path | None = None) -> duckdb.DuckDBPyConnection:
    target = path or warehouse_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(target))


def init_warehouse(conn: duckdb.DuckDBPyConnection) -> None:
    for spec in SOURCES.values():
        duckdb_loader.ensure_raw_table(conn, spec.raw_table, PAYLOAD_COLUMNS[spec.name])
        if spec.quarantine_table:
            quarantine.ensure_quarantine_table(conn, spec.quarantine_table)
    watermarks.ensure_watermark_table(conn)
    lineage.ensure_lineage_table(conn)


def _source_root() -> Path:
    override = os.environ.get("DATA_SOURCE_ROOT")
    return Path(override) if override else project_root() / "data" / "source"


def _source_files(source_name: str) -> list[Path]:
    base = _source_root()
    if source_name == "customers":
        return [base / "customers.csv"]
    if source_name == "regions":
        return [base / "regions.csv"]
    directory = base / source_name
    return sorted(directory.glob("*.ndjson")) if directory.exists() else []


def _extract(conn, source_name: str, spec, full: bool, api_base_url: str | None, pg_dsn: str | None):
    """Returns (records, malformed_entries, max_observed_watermark, extract_stats)."""
    shape = spec.shape

    if shape == "csv":
        records, entries = [], []
        for path in _source_files(source_name):
            records.extend(csv_file.extract_csv(path, source_name))
        return records, entries, None, {}

    if shape == "ndjson":
        records, entries = [], []
        max_wm = None if full else watermarks.get_watermark(conn, source_name)
        overall_max = None
        skipped_replayed = 0
        for path in _source_files(source_name):
            file_records, malformed = ndjson_file.extract_ndjson(path)
            for line_number, rec in file_records:
                wm_value = rec.get(spec.watermark_field) if spec.watermark_field else None
                if max_wm is not None and wm_value is not None and str(wm_value) <= max_wm:
                    skipped_replayed += 1
                    continue
                records.append((line_number, rec))
                if wm_value is not None and (overall_max is None or str(wm_value) > overall_max):
                    overall_max = str(wm_value)
            for m in malformed:
                entries.append({
                    "source_file": m.source_file,
                    "source_row_number": m.line_number,
                    "reason": "malformed_json",
                    "error_detail": m.error,
                    "raw_record": m.raw_line,
                })
        return records, entries, overall_max, {"skipped_replayed": skipped_replayed}

    if shape == "api":
        base_url = api_base_url or env("PRODUCTS_API_URL", "http://localhost:8100")
        payload = api_extractor.fetch_products(base_url)
        records = [(idx, rec) for idx, rec in enumerate(payload, start=1)]
        return records, [], None, {}

    if shape == "rdbms":
        dsn = pg_dsn or _pg_dsn()
        table = source_name
        columns = [name for name, _ in PAYLOAD_COLUMNS[source_name]]
        since = None if full else watermarks.get_watermark(conn, source_name)
        rows, max_wm = rdbms.extract_watermarked(dsn, "source_oltp", table, columns, spec.watermark_field, since)
        records = [(idx, row) for idx, row in enumerate(rows, start=1)]
        return records, [], max_wm, {}

    raise ValueError(f"Unsupported source shape: {shape}")


def _integrity_gate(conn, source_name: str, spec, records) -> tuple[list, list[dict]]:
    """Referential-integrity gating (not business logic): orders referencing an
    unknown customer are quarantined with a reason instead of flowing downstream."""
    if source_name != "orders" or not records:
        return records, []

    exists = conn.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'raw' AND table_name = 'customers'
        """
    ).fetchone()[0]
    if not exists:
        return records, []

    known_ids = {row[0] for row in conn.execute("SELECT DISTINCT customer_id FROM raw.customers").fetchall()}
    kept, gated = [], []
    for row_number, record in records:
        if str(record.get("customer_id")) in known_ids:
            kept.append((row_number, record))
        else:
            gated.append({
                "source_file": "orders",
                "source_row_number": row_number,
                "reason": "invalid_fk_customer",
                "error_detail": f"customer_id {record.get('customer_id')} not present in raw.customers",
                "raw_record": str(record)[:2000],
            })
    return kept, gated


def _pg_dsn() -> str:
    return (
        f"host={env('SOURCE_PG_HOST', 'localhost')} port={env('SOURCE_PG_PORT', '5433')} "
        f"dbname={env('SOURCE_PG_DB', 'sourcedb')} user={env('SOURCE_PG_USER', 'source_reader')} "
        f"password={env('SOURCE_PG_PASSWORD', '')}"
    )


def run_source(
    conn: duckdb.DuckDBPyConnection,
    source_name: str,
    batch_id: str | None = None,
    full: bool = False,
    api_base_url: str | None = None,
    pg_dsn: str | None = None,
) -> dict:
    """Extract → integrity-gate → atomic load → quarantine → lineage → watermark.

    Failure semantics: any exception aborts the batch atomically (zero partial
    rows) and the watermark is left untouched.
    """
    spec = SOURCES[source_name]
    batch_id = batch_id or new_batch_id()
    ingested_at = dt.datetime.now(dt.UTC).isoformat()

    records, malformed_entries, max_observed_wm, extract_stats = _extract(
        conn, source_name, spec, full, api_base_url, pg_dsn
    )

    kept_records, gated_entries = _integrity_gate(conn, source_name, spec, records)

    payload_cols = [name for name, _ in PAYLOAD_COLUMNS[source_name]]
    load_stats = duckdb_loader.load_batch(
        conn, spec.raw_table, payload_cols, batch_id,
        kept_records, source_name, f"{spec.shape}:{source_name}", ingested_at,
        replace_all=spec.watermark_field is None,
    )

    quarantine_entries = malformed_entries + gated_entries
    quarantined = 0
    if spec.quarantine_table:
        quarantined = quarantine.quarantine_records(
            conn, spec.quarantine_table, quarantine_entries, source_name, batch_id, ingested_at
        )

    if kept_records or quarantined:
        lineage.record_lineage(
            conn, batch_id=batch_id, source_name=source_name,
            source_ref=f"{spec.shape}:{source_name}", target_raw_table=spec.raw_table,
            ingested_at=ingested_at, rows_extracted=len(records),
            rows_loaded=len(kept_records), rows_quarantined=quarantined,
            run_mode="full" if full else ("incremental" if spec.watermark_field else "snapshot"),
        )

    watermark_advanced = False
    if spec.watermark_field and max_observed_wm is not None:
        watermark_advanced = watermarks.advance_if_newer(
            conn, source_name, spec.watermark_field, str(max_observed_wm), batch_id
        )

    return {
        "batch_id": batch_id,
        "source": source_name,
        "extracted": len(records),
        "loaded": load_stats["loaded_rows"],
        "replaced_prior_rows": load_stats["replaced_prior_rows"],
        "quarantined": quarantined,
        "duplicates_in_batch": load_stats["duplicates_in_batch"],
        "duplicates_vs_existing_batches": load_stats["duplicates_vs_existing_batches"],
        "skipped_replayed": extract_stats.get("skipped_replayed", 0),
        "watermark_advanced": watermark_advanced,
        "max_observed_watermark": max_observed_wm,
    }
