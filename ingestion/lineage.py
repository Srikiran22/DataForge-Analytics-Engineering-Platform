import duckdb

LINEAGE_DDL = """
CREATE TABLE IF NOT EXISTS lineage.batch_lineage (
    batch_id VARCHAR NOT NULL,
    source_name VARCHAR NOT NULL,
    source_ref VARCHAR,
    target_raw_table VARCHAR NOT NULL,
    ingested_at TIMESTAMP NOT NULL,
    rows_extracted BIGINT,
    rows_loaded BIGINT,
    rows_quarantined BIGINT,
    run_mode VARCHAR,
    PRIMARY KEY (batch_id, source_name, source_ref)
)
"""


def ensure_lineage_table(conn: duckdb.DuckDBPyConnection):
    conn.execute("CREATE SCHEMA IF NOT EXISTS lineage")
    conn.execute(LINEAGE_DDL)


def record_lineage(
    conn: duckdb.DuckDBPyConnection,
    batch_id: str,
    source_name: str,
    source_ref: str,
    target_raw_table: str,
    ingested_at: str,
    rows_extracted: int,
    rows_loaded: int,
    rows_quarantined: int,
    run_mode: str,
) -> None:
    """Insert-or-replace lineage so re-running a batch updates its own entry."""
    ensure_lineage_table(conn)
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(
            "DELETE FROM lineage.batch_lineage WHERE batch_id = ? AND source_name = ? AND source_ref = ?",
            [batch_id, source_name, source_ref],
        )
        conn.execute(
            """
            INSERT INTO lineage.batch_lineage
                (batch_id, source_name, source_ref, target_raw_table, ingested_at,
                 rows_extracted, rows_loaded, rows_quarantined, run_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [batch_id, source_name, source_ref, target_raw_table, ingested_at,
             rows_extracted, rows_loaded, rows_quarantined, run_mode],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
