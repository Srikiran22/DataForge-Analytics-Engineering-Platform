import duckdb


def ensure_watermark_table(conn: duckdb.DuckDBPyConnection):
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw.ingestion_watermarks (
            source_name VARCHAR NOT NULL,
            watermark_field VARCHAR NOT NULL,
            watermark_value VARCHAR NOT NULL,
            advanced_at TIMESTAMP NOT NULL,
            last_batch_id VARCHAR
        )
    """)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_watermarks_source ON raw.ingestion_watermarks (source_name)"
    )


def get_watermark(conn: duckdb.DuckDBPyConnection, source_name: str) -> str | None:
    row = conn.execute(
        "SELECT watermark_value FROM raw.ingestion_watermarks WHERE source_name = ?",
        [source_name],
    ).fetchone()
    return row[0] if row else None


def advance_watermark(
    conn: duckdb.DuckDBPyConnection,
    source_name: str,
    watermark_field: str,
    watermark_value: str,
    batch_id: str,
) -> None:
    """Called ONLY after the corresponding batch has committed successfully."""
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(
            """
            INSERT INTO raw.ingestion_watermarks
                (source_name, watermark_field, watermark_value, advanced_at, last_batch_id)
            VALUES (?, ?, ?, current_timestamp, ?)
            ON CONFLICT (source_name) DO UPDATE SET
                watermark_value = excluded.watermark_value,
                watermark_field = excluded.watermark_field,
                advanced_at = excluded.advanced_at,
                last_batch_id = excluded.last_batch_id
            """,
            [source_name, watermark_field, watermark_value, batch_id],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def advance_if_newer(
    conn: duckdb.DuckDBPyConnection,
    source_name: str,
    watermark_field: str,
    candidate_value: str,
    batch_id: str,
) -> bool:
    """Advance only when candidate > stored value; monotonic guard."""
    current = get_watermark(conn, source_name)
    if current is not None and candidate_value <= current:
        return False
    advance_watermark(conn, source_name, watermark_field, candidate_value, batch_id)
    return True
