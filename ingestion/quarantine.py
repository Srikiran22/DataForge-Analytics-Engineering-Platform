import duckdb


def ensure_quarantine_table(conn: duckdb.DuckDBPyConnection, table: str):
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {table.split('.')[0]}")
    ddl = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            source_file VARCHAR,
            source_row_number BIGINT,
            reason VARCHAR NOT NULL,
            error_detail VARCHAR,
            raw_record VARCHAR,
            _source_name VARCHAR,
            _batch_id VARCHAR,
            _ingested_at TIMESTAMP
        )
    """
    conn.execute(ddl)


def quarantine_records(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    entries: list[dict],
    source_name: str,
    batch_id: str,
    ingested_at: str,
) -> int:
    """Write rejected records with an explicit reason. Never raises on empty input."""
    if not entries:
        return 0
    ensure_quarantine_table(conn, table)
    columns = [
        "source_file", "source_row_number", "reason", "error_detail",
        "raw_record", "_source_name", "_batch_id", "_ingested_at",
    ]
    placeholders = ", ".join(["?"] * len(columns))
    sql = f'INSERT INTO {table} ({", ".join(columns)}) VALUES ({placeholders})'
    rows = [
        [
            e.get("source_file"),
            e.get("source_row_number"),
            e["reason"],
            e.get("error_detail"),
            e.get("raw_record"),
            source_name,
            batch_id,
            ingested_at,
        ]
        for e in entries
    ]
    conn.executemany(sql, rows)
    return len(rows)


def quarantine_counts_by_reason(conn: duckdb.DuckDBPyConnection, table: str) -> dict:
    rows = conn.execute(
        f"SELECT reason, COUNT(*) FROM {table} GROUP BY reason ORDER BY reason"
    ).fetchall() if _table_exists(conn, table) else []
    return {reason: count for reason, count in rows}


def _table_exists(conn: duckdb.DuckDBPyConnection, table: str) -> bool:
    schema, name = table.split(".")
    row = conn.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = ? AND table_name = ?
        """,
        [schema, name],
    ).fetchone()
    return bool(row[0])
