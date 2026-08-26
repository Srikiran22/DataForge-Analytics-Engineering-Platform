"""Failure semantics proven empirically:
- constraint 5: partial failure (crash mid-insert) leaves zero partial rows;
- constraint 6: duplicate batch submission does not duplicate data;
- constraint 7: failed ingestion never advances the watermark.
"""

import json

import pytest

from ingestion import pipeline, watermarks
from ingestion.loaders import duckdb_loader
from tests.integration.conftest import CUSTOMER_A, ORDER_1, count


class CrashingConn:
    """Proxy connection that crashes on INSERT execution for a given table,
    simulating a process death inside the batch transaction."""

    def __init__(self, real, fail_on_sql_fragment):
        self._real = real
        self._frag = fail_on_sql_fragment

    def __getattr__(self, name):
        return getattr(self._real, name)

    def execute(self, sql, *args, **kwargs):
        if self._frag in sql:
            raise RuntimeError("simulated crash mid-load")
        return self._real.execute(sql, *args, **kwargs)


@pytest.fixture()
def seeded_customers(wh, source_dir):
    source_dir["write_customers"]([CUSTOMER_A])
    pipeline.run_source(wh, "customers", batch_id="c-batch", full=True)


def _orders_payload_cols():
    return [name for name, _ in pipeline.PAYLOAD_COLUMNS["orders"]]


def test_crash_mid_insert_rolls_back_entire_batch(wh, seeded_customers):
    records = [
        (i, dict(ORDER_1, order_id=f"O{i}", updated_at=f"2026-01-01T1{i}:00:00Z",
                 order_ts=f"2026-01-01T1{i}:00:00Z"))
        for i in range(5)
    ]

    crashing = CrashingConn(wh, "INSERT INTO raw.orders")
    with pytest.raises(RuntimeError, match="simulated crash"):
        duckdb_loader.load_batch(
            crashing, "raw.orders", _orders_payload_cols(), "doomed-batch",
            records, "orders", "ndjson:orders", "2026-08-26T00:00:00Z",
        )

    assert count(wh, "raw.orders") == 0
    assert watermarks.get_watermark(wh, "orders") is None


def test_failed_load_does_not_advance_watermark_even_with_prior_state(
    wh, source_dir, seeded_customers, monkeypatch
):
    source_dir["write_orders_day"]("2026-01-01", [
        json.dumps(dict(ORDER_1, order_id="O1", updated_at="2026-01-01T12:00:00Z")),
    ])
    pipeline.run_source(wh, "orders", batch_id="good-batch")
    wm_before = watermarks.get_watermark(wh, "orders")
    assert wm_before == "2026-01-01T12:00:00Z"

    source_dir["write_orders_day"]("2026-02-01", [
        json.dumps(dict(ORDER_1, order_id="O2", updated_at="2026-02-01T12:00:00Z")),
    ])

    def failing_load(*args, **kwargs):
        raise RuntimeError("load exploded after extraction")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pipeline.duckdb_loader, "load_batch", failing_load)
        with pytest.raises(RuntimeError, match="load exploded"):
            pipeline.run_source(wh, "orders", batch_id="bad-batch")

    assert watermarks.get_watermark(wh, "orders") == wm_before
    assert count(wh, "raw.orders", "order_id = 'O2'") == 0

    recovered = pipeline.run_source(wh, "orders", batch_id="recovery-batch")
    assert recovered["loaded"] == 1
    assert watermarks.get_watermark(wh, "orders") == "2026-02-01T12:00:00Z"


def test_duplicate_batch_submission_never_duplicates_data(wh, source_dir, seeded_customers):
    source_dir["write_orders_day"]("2026-03-01", [
        json.dumps(dict(ORDER_1, order_id=f"O{i}", updated_at=f"2026-03-01T1{i}:00:00Z"))
        for i in range(4)
    ])

    pipeline.run_source(wh, "orders", batch_id="same-batch-id")
    rows_after_first = count(wh, "raw.orders")
    assert rows_after_first == 4

    second = pipeline.run_source(wh, "orders", batch_id="same-batch-id")
    assert second["extracted"] == 0 and second["loaded"] == 0
    assert count(wh, "raw.orders") == 4

    third = pipeline.run_source(wh, "orders", batch_id="same-batch-id", full=True)
    assert third["loaded"] == 4 and third["replaced_prior_rows"] == 4
    assert count(wh, "raw.orders") == 4
    assert count(wh, "raw.orders", "_batch_id = 'same-batch-id'") == 4


def test_loader_replace_semantics_direct(wh):
    duckdb_loader.ensure_raw_table(wh, "raw.orders", pipeline.PAYLOAD_COLUMNS["orders"])
    records = [(1, {"order_id": "O1"})]
    payload_cols = [name for name, _ in pipeline.PAYLOAD_COLUMNS["orders"]]

    duckdb_loader.load_batch(wh, "raw.orders", payload_cols, "b1", records, "orders", "f", "2026-08-26T00:00:00Z")
    duckdb_loader.load_batch(wh, "raw.orders", payload_cols, "b1", records, "orders", "f", "2026-08-26T00:00:00Z")

    assert count(wh, "raw.orders") == 1
