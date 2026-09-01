import datetime as dt
import decimal
import re
from collections.abc import Iterator

import psycopg


def _normalize(value):
    """Convert DB-native types to JSON-safe equivalents so every source shape
    feeds the same bulk loader contract (raw stays VARCHAR-typed)."""
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat(sep=" ")
    if isinstance(value, decimal.Decimal):
        return str(value)
    return value


def connect(dsn: str):
    return psycopg.connect(dsn)


def _validate_identifier(name: str) -> None:
    """Validate a SQL identifier (schema, table, column, or field name).

    Rules enforced:
    - Must be a str
    - Must start with a letter (A-Z, a-z) or underscore
    - May contain only letters, digits, and underscores
    - No dots, whitespace, or SQL metacharacters allowed

    Raises ValueError with the message "Invalid SQL identifier" when the
    identifier is not acceptable. Tests rely on this exact message.
    """
    if not isinstance(name, str):
        raise ValueError("Invalid SQL identifier")
    # Simple conservative pattern: starts with letter or underscore, then letters/digits/underscores
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValueError("Invalid SQL identifier")


def _stream_rows(cur, columns: list[str], watermark_field: str | None) -> Iterator[tuple[dict, str | None]]:
    """Stream rows from cursor using fetchmany to avoid memory spikes.

    Yields (record_dict, watermark_value) for each row.
    """
    fetch_size = 10000
    while True:
        rows = cur.fetchmany(fetch_size)
        if not rows:
            break
        for row in rows:
            record = {col: _normalize(val) for col, val in zip(columns, row, strict=True)}
            wm_value = record[watermark_field] if watermark_field else None
            yield record, str(wm_value) if wm_value is not None else None


def extract_watermarked(
    dsn: str,
    schema: str,
    table: str,
    columns: list[str],
    watermark_field: str | None,
    since_value: str | None,
) -> tuple[list[dict], str | None]:
    """Extract rows from the OLTP source, optionally watermarked by updated_at.

    Parameterized queries only. Returns (rows_as_dicts, max_observed_watermark).
    The caller owns watermark persistence; this function never writes state.
    Uses fetchmany for memory-efficient streaming.
    """
    # Validate identifiers strictly before composing the SQL. This defends against
    # accidental SQL injection via schema/table/column names. The tests expect
    # ValueError("Invalid SQL identifier") for malicious inputs.
    _validate_identifier(schema)
    _validate_identifier(table)
    for col in columns:
        _validate_identifier(col)
    if watermark_field:
        _validate_identifier(watermark_field)

    query = f'SELECT {", ".join(columns)} FROM {schema}.{table}'
    params: list[str] = []
    if watermark_field and since_value is not None:
        query += f" WHERE {watermark_field} > %s"
        params.append(since_value)
    if watermark_field:
        query += f" ORDER BY {watermark_field}"

    rows: list[dict] = []
    max_watermark = since_value
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(query, params)
        for record, wm_value in _stream_rows(cur, columns, watermark_field):
            rows.append(record)
            if wm_value is not None and (max_watermark is None or wm_value > max_watermark):
                max_watermark = wm_value
    return rows, max_watermark
