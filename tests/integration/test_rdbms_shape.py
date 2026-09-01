"""RDBMS source shape against real Postgres (docker-compose service).

These tests require a reachable source database. They are skipped with an
explicit marker when it is unavailable so the rest of the suite stays green;
the Phase 2 gate report states plainly whether they ran.
"""

import sys

import psycopg
import pytest

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ingestion import pipeline, watermarks


def _pg_reachable() -> bool:
    try:
        from ingestion.pipeline import _pg_dsn

        with psycopg.connect(_pg_dsn(), connect_timeout=3):
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_reachable(), reason="source Postgres not reachable (start docker compose)"
)


def test_payments_watermarked_extraction_and_late_rows(wh):
    from ingestion.extractors import rdbms

    columns = ["payment_id", "order_id", "amount_cents", "status", "method", "event_ts", "updated_at"]
    rows, max_wm = rdbms.extract_watermarked(
        _dsn(), "source_oltp", "payments", columns, "updated_at", None
    )

    assert rows, "payments table must contain seeded rows"
    assert max_wm is not None

    late_cutoff = "2000-01-01 00:00:00"
    rows_since, _max_wm2 = rdbms.extract_watermarked(
        _dsn(), "source_oltp", "payments", columns, "updated_at", late_cutoff
    )
    assert len(rows_since) == len(rows)

    rows_after_max, _ = rdbms.extract_watermarked(
        _dsn(), "source_oltp", "payments", columns, "updated_at", max_wm
    )
    assert rows_after_max == []


def test_full_pipeline_load_from_rdbms_shape(wh):
    stats = pipeline.run_source(wh, "order_items", batch_id="pg-items-1")
    assert stats["loaded"] > 0
    before = wh.execute("SELECT COUNT(*) FROM raw.order_items").fetchone()[0]

    rerun = pipeline.run_source(wh, "order_items", batch_id="pg-items-1")
    after = wh.execute("SELECT COUNT(*) FROM raw.order_items").fetchone()[0]
    assert rerun["extracted"] == 0
    assert before == after

    full_rerun = pipeline.run_source(wh, "order_items", batch_id="pg-items-1", full=True)
    final = wh.execute("SELECT COUNT(*) FROM raw.order_items").fetchone()[0]
    assert full_rerun["replaced_prior_rows"] == before
    assert full_rerun["loaded"] == before
    assert final == before


def test_inventory_levels_load(wh):
    stats = pipeline.run_source(wh, "inventory_levels", batch_id="pg-inv-1")
    assert stats["loaded"] > 0


def test_rdbms_incremental_second_run_extracts_zero_new_rows(wh):
    first = pipeline.run_source(wh, "payments", batch_id="pg-pay-1")
    assert first["loaded"] > 0
    assert first["watermark_advanced"] is True
    rows_after_first = wh.execute("SELECT COUNT(*) FROM raw.payments").fetchone()[0]

    second = pipeline.run_source(wh, "payments", batch_id="pg-pay-2")
    assert second["extracted"] == 0
    assert second["loaded"] == 0
    assert second["watermark_advanced"] is False
    assert wh.execute("SELECT COUNT(*) FROM raw.payments").fetchone()[0] == rows_after_first


def test_rdbms_duplicate_batch_rerun_never_duplicates(wh):
    pipeline.run_source(wh, "order_items", batch_id="pg-dup-batch")
    count_a = wh.execute("SELECT COUNT(*) FROM raw.order_items").fetchone()[0]

    second = pipeline.run_source(wh, "order_items", batch_id="pg-dup-batch")
    assert second["extracted"] == 0 and second["loaded"] == 0
    count_b = wh.execute("SELECT COUNT(*) FROM raw.order_items").fetchone()[0]
    assert count_a == count_b

    third = pipeline.run_source(wh, "order_items", batch_id="pg-dup-batch", full=True)
    count_c = wh.execute("SELECT COUNT(*) FROM raw.order_items").fetchone()[0]
    assert third["replaced_prior_rows"] == count_a
    assert third["loaded"] == count_a
    assert count_c == count_a

    batches = wh.execute(
        "SELECT COUNT(DISTINCT _batch_id) FROM raw.order_items"
    ).fetchone()[0]
    assert batches == 1


def test_rdbms_failed_load_does_not_advance_watermark(wh, monkeypatch):
    pipeline.run_source(wh, "payments", batch_id="pg-wm-good")
    wm_before = watermarks.get_watermark(wh, "payments")
    rows_before = wh.execute("SELECT COUNT(*) FROM raw.payments").fetchone()[0]
    assert wm_before is not None

    def failing_load(*args, **kwargs):
        raise RuntimeError("rdbms load exploded")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pipeline.duckdb_loader, "load_batch", failing_load)
        with pytest.raises(RuntimeError, match="rdbms load exploded"):
            pipeline.run_source(wh, "payments", batch_id="pg-wm-bad")

    assert watermarks.get_watermark(wh, "payments") == wm_before
    assert wh.execute("SELECT COUNT(*) FROM raw.payments").fetchone()[0] == rows_before

    recovered = pipeline.run_source(wh, "payments", batch_id="pg-wm-recovery")
    assert recovered["loaded"] == 0
    assert watermarks.get_watermark(wh, "payments") == wm_before


def _dsn() -> str:
    from ingestion.pipeline import _pg_dsn

    return _pg_dsn()
