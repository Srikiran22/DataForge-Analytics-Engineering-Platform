import duckdb

from ingestion import quarantine
from ingestion.extractors.ndjson_file import extract_ndjson


def write_ndjson(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_parseable_lines_extracted_malformed_collected(tmp_path):
    p = tmp_path / "dt=2026-01-01.ndjson"
    write_ndjson(p, [
        '{"order_id": "O1", "amount": 100}',
        '{"order_id": "O2", "amount"',            # truncated JSON (I-04 shape)
        'not json at all',                         # garbage line
        '{"order_id": "O3"}',
    ])

    records, malformed = extract_ndjson(p)

    assert [r[1]["order_id"] for r in records] == ["O1", "O3"]
    assert len(malformed) == 2
    assert malformed[0].line_number == 2
    assert malformed[1].line_number == 3
    assert malformed[0].error and malformed[1].error


def test_quarantine_writer_records_reasons_and_counts(tmp_path):
    conn = duckdb.connect(":memory:")
    table = "raw.quarantine_orders"

    entries = [
        {"source_file": "x.ndjson", "source_row_number": 2, "reason": "malformed_json",
         "error_detail": "e1", "raw_record": '{"a"'},
        {"source_file": "orders", "source_row_number": 9, "reason": "invalid_fk_customer",
         "error_detail": "missing customer", "raw_record": '{"customer_id": "C999999"}'},
    ]

    written = quarantine.quarantine_records(conn, table, entries, "orders", "b1", "2026-08-26T00:00:00Z")
    again = quarantine.quarantine_records(conn, table, [], "orders", "b1", "2026-08-26T00:00:00Z")

    counts = quarantine.quarantine_counts_by_reason(conn, table)

    assert written == 2
    assert again == 0
    assert counts == {"invalid_fk_customer": 1, "malformed_json": 1}
    conn.close()
