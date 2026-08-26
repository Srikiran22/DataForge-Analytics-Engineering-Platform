import duckdb
import pytest

from ingestion import watermarks


@pytest.fixture()
def conn():
    conn = duckdb.connect(":memory:")
    watermarks.ensure_watermark_table(conn)
    yield conn
    conn.close()


def test_get_returns_none_before_first_advance(conn):
    assert watermarks.get_watermark(conn, "orders") is None


def test_advance_sets_value(conn):
    watermarks.advance_watermark(conn, "orders", "updated_at", "2026-08-01T00:00:00Z", "b1")
    assert watermarks.get_watermark(conn, "orders") == "2026-08-01T00:00:00Z"


def test_advance_if_newer_is_monotonic(conn):
    assert watermarks.advance_if_newer(conn, "orders", "updated_at", "2026-08-01T00:00:00Z", "b1") is True
    assert watermarks.advance_if_newer(conn, "orders", "updated_at", "2026-07-01T00:00:00Z", "b2") is False
    assert watermarks.get_watermark(conn, "orders") == "2026-08-01T00:00:00Z"


def test_equal_watermark_does_not_advance(conn):
    watermarks.advance_if_newer(conn, "orders", "updated_at", "2026-08-01T00:00:00Z", "b1")
    assert watermarks.advance_if_newer(conn, "orders", "updated_at", "2026-08-01T00:00:00Z", "b2") is False


def test_sources_are_independent(conn):
    watermarks.advance_if_newer(conn, "orders", "updated_at", "2026-08-01T00:00:00Z", "b1")
    watermarks.advance_if_newer(conn, "payments", "updated_at", "2026-06-01T00:00:00Z", "b2")
    assert watermarks.get_watermark(conn, "orders") == "2026-08-01T00:00:00Z"
    assert watermarks.get_watermark(conn, "payments") == "2026-06-01T00:00:00Z"
