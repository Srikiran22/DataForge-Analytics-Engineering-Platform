import psycopg


def connect(dsn: str):
    return psycopg.connect(dsn)


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
    """
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
        for row in cur.fetchall():
            record = dict(zip(columns, row, strict=True))
            rows.append(record)
            if watermark_field:
                candidate = record[watermark_field]
                if isinstance(candidate, str):
                    candidate_str = candidate
                else:
                    candidate_str = candidate.isoformat(sep=" ")
                if max_watermark is None or candidate_str > str(max_watermark):
                    max_watermark = candidate_str
    return rows, max_watermark
