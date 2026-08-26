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

from ingestion import pipeline


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
    assert rerun["replaced_prior_rows"] == before == after


def test_inventory_levels_load(wh):
    stats = pipeline.run_source(wh, "inventory_levels", batch_id="pg-inv-1")
    assert stats["loaded"] > 0


def _dsn() -> str:
    from ingestion.pipeline import _pg_dsn

    return _pg_dsn()
