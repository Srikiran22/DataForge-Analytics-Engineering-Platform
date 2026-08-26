import json
import tempfile
from pathlib import Path

import duckdb

from ingestion.sources import INGESTION_METADATA_COLUMNS, SOURCES


def ensure_raw_table(conn: duckdb.DuckDBPyConnection, table: str, payload_columns: list[tuple[str, str]]):
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {table.split('.')[0]}")
    all_columns = list(payload_columns) + list(INGESTION_METADATA_COLUMNS)
    column_ddl = ", ".join(f'"{name}" {typ}' for name, typ in all_columns)
    conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({column_ddl})")


def detect_duplicates(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    natural_key: tuple[str, ...],
    records: list[tuple[int, dict]],
    batch_id: str,
) -> dict:
    """Count record-level duplicate occurrences. Raw PRESERVES duplicates;
    detection here is for observability and replay awareness."""
    if not records:
        return {"duplicates_in_batch": 0, "duplicates_vs_existing_batches": 0}

    key_expr = ", ".join(f'"{c}"' for c in natural_key)
    keys = [tuple(str(record.get(c)) for c in natural_key) for _, record in records]

    dup_in_batch = 0
    seen: set[tuple[str, ...]] = set()
    for k in keys:
        if k in seen:
            dup_in_batch += 1
        seen.add(k)

    dup_vs_existing = 0
    if seen:
        existing_rows = conn.execute(
            f"SELECT DISTINCT {key_expr} FROM {table} WHERE _batch_id <> ?", [batch_id]
        ).fetchall()
        existing = {tuple(str(v) for v in row) for row in existing_rows}
        dup_vs_existing = sum(1 for k in keys if k in existing)

    return {
        "duplicates_in_batch": dup_in_batch,
        "duplicates_vs_existing_batches": dup_vs_existing,
    }


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _bulk_insert_via_json(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    payload_columns: list[str],
    batch_id: str,
    records: list[tuple[int, dict]],
    source_name: str,
    source_file: str,
    ingested_at: str,
) -> None:
    """Bulk-load via DuckDB's read_json: C++ speed instead of row-wise
    executemany (which measured ~160s for 40k rows)."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".ndjson", delete=False, encoding="utf-8", newline="\n"
    )
    try:
        for row_number, record in records:
            obj = {c: record.get(c) for c in payload_columns}
            obj["__rn"] = row_number
            tmp.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
        tmp.close()

        json_columns = {c: "VARCHAR" for c in payload_columns}
        json_columns["__rn"] = "BIGINT"
        cols_spec = ", ".join(f"'{name}': '{typ}'" for name, typ in json_columns.items())
        select_cols = ", ".join(f'"{c}"' for c in payload_columns)
        meta_cols = (
            f"{_sql_string(source_name)}, {_sql_string(batch_id)}, "
            f"{_sql_string(ingested_at)}::TIMESTAMP, {_sql_string(source_file)}, __rn"
        )
        conn.execute(
            f"""
            INSERT INTO {table}
                ({select_cols}, "_source_name", "_batch_id", "_ingested_at", "_source_file", "_source_row_number")
            SELECT {select_cols}, {meta_cols}
            FROM read_json({_sql_string(str(Path(tmp.name).resolve()))},
                          columns={{{cols_spec}}},
                          format='newline_delimited')
            """
        )
    finally:
        try:
            Path(tmp.name).unlink()
        except OSError:
            pass


def load_batch(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    payload_columns: list[str],
    batch_id: str,
    records: list[tuple[int, dict]],
    source_name: str,
    source_file: str,
    ingested_at: str,
    replace_all: bool = False,
) -> dict:
    """Load one batch atomically.

    Semantics:
    - Whole batch runs in a single transaction: any failure rolls back every row.
    - Re-running the same batch_id replaces prior rows for that id (idempotency).
    - A run that extracted zero records leaves previously committed rows intact.
    - replace_all=True (snapshot-shaped sources without watermarks): a successful
      new batch REPLACES the entire table contents - repeated full exports do
      not accumulate stale snapshots.
    - Duplicates are detected and reported but preserved in raw (fidelity);
      deduplication is a staging-layer decision.
    """
    existing_batch_count = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE _batch_id = ?", [batch_id]
    ).fetchone()[0]

    if not records:
        return {
            "loaded_rows": 0,
            "replaced_prior_rows": 0,
            **detect_duplicates(conn, table, SOURCES[source_name].natural_key, [], batch_id),
        }

    natural_key = SOURCES[source_name].natural_key
    dup_stats = detect_duplicates(conn, table, natural_key, records, batch_id)

    conn.execute("BEGIN TRANSACTION")
    try:
        if existing_batch_count:
            conn.execute(f"DELETE FROM {table} WHERE _batch_id = ?", [batch_id])
        elif replace_all:
            replaced = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            conn.execute(f"DELETE FROM {table}")
            existing_batch_count = replaced

        _bulk_insert_via_json(
            conn, table, payload_columns, batch_id, records,
            source_name, source_file, ingested_at,
        )

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return {
        "loaded_rows": len(records),
        "replaced_prior_rows": existing_batch_count,
        **dup_stats,
    }
