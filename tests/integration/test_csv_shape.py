"""CSV source shape: full load + empirical idempotency proof.

Constraint #4: idempotency is proven by RUNNING loads twice and comparing
row counts and content checksums - not by reading code.
"""



def _checksum(conn, table):
    row = conn.execute(f"""
        SELECT MD5(STRING_AGG(row_hash, '|' ORDER BY row_hash)) FROM (
            SELECT MD5(CAST((customer_id, email, updated_at) AS VARCHAR)) AS row_hash
            FROM {table}
        )
    """).fetchone()
    return row[0]


def test_csv_full_load_then_identical_rerun_is_idempotent(wh, source_dir):
    from ingestion import pipeline

    source_dir["write_customers"]([
        conftest_customer("C1"),
        conftest_customer("C2"),
    ])

    run1 = pipeline.run_source(wh, "customers", batch_id="batch-a", full=True)
    rows_after_run1 = count_of(wh)
    checksum_after_run1 = _checksum(wh, "raw.customers")

    assert run1["loaded"] == 2
    assert rows_after_run1 == 2

    run2 = pipeline.run_source(wh, "customers", batch_id="batch-a", full=True)
    rows_after_run2 = count_of(wh)
    checksum_after_run2 = _checksum(wh, "raw.customers")

    assert run2["loaded"] == 2
    assert run2["replaced_prior_rows"] == 2
    assert rows_after_run2 == rows_after_run1 == 2
    assert checksum_after_run2 == checksum_after_run1

    batch_count = wh.execute(
        "SELECT COUNT(DISTINCT _batch_id) FROM raw.customers"
    ).fetchone()[0]
    assert batch_count == 1


def test_new_full_export_replaces_stale_snapshot_not_accumulates(wh, source_dir):
    """Snapshot-shaped sources (no watermark): each successful full load
    replaces prior contents - repeated exports never accumulate copies."""
    from ingestion import pipeline

    source_dir["write_customers"]([conftest_customer("C1")])
    pipeline.run_source(wh, "customers", batch_id="batch-a", full=True)
    assert count_of(wh) == 1

    source_dir["write_customers"]([conftest_customer("C1"), conftest_customer("C2")])
    run = pipeline.run_source(wh, "customers", batch_id="batch-b", full=True)

    total = count_of(wh)
    distinct_ids = wh.execute(
        "SELECT COUNT(DISTINCT customer_id) FROM raw.customers"
    ).fetchone()[0]
    batches_present = wh.execute(
        "SELECT COUNT(DISTINCT _batch_id) FROM raw.customers"
    ).fetchone()[0]

    assert run["duplicates_vs_existing_batches"] >= 1
    assert run["replaced_prior_rows"] == 1
    assert total == 2
    assert distinct_ids == 2
    assert batches_present == 1


def test_metadata_columns_present_on_every_row(wh, source_dir):
    from ingestion import pipeline

    source_dir["write_customers"]([conftest_customer("C1")])
    pipeline.run_source(wh, "customers", batch_id="meta-batch", full=True)

    row = wh.execute("""
        SELECT _source_name, _batch_id, _source_file, _source_row_number, _ingested_at IS NOT NULL
        FROM raw.customers LIMIT 1
    """).fetchone()

    assert row[0] == "customers"
    assert row[1] == "meta-batch"
    assert row[2].endswith("customers.csv") or row[2].startswith("csv:")
    assert row[3] is not None
    assert row[4] is True


def count_of(conn):
    return conn.execute("SELECT COUNT(*) FROM raw.customers").fetchone()[0]


def conftest_customer(cid):
    return {"customer_id": cid, "first_name": "A", "last_name": "B",
            "email": f"{cid.lower()}@x.com", "city": "X", "region_id": "RG01",
            "segment": "consumer", "signup_date": "2024-09-01",
            "updated_at": "2024-09-01T10:00:00Z"}
