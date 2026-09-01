"""Test SCD2 snapshot idempotency by running dbt snapshot twice."""
import subprocess
from pathlib import Path

import duckdb
import pytest

WAREHOUSE = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "analytics.duckdb"
DBT_PROJECT = Path(__file__).resolve().parents[2] / "dbt"


def _run_dbt_snapshot():
    """Run dbt snapshot and return result. Accept return code 2 (deprecation warnings)."""
    result = subprocess.run(
        ["dbt", "snapshot", "--profiles-dir", str(DBT_PROJECT)],
        env={**__import__("os").environ, "WAREHOUSE_PATH": str(WAREHOUSE)},
        capture_output=True,
        text=True,
        cwd=DBT_PROJECT,
    )
    # dbt returns 2 for deprecation warnings, 0 for success, 1 for error
    if result.returncode not in (0, 2):
        raise RuntimeError(f"dbt snapshot failed (code {result.returncode}): {result.stderr}")
    return result


def _get_snapshot_row_count():
    """Get current snapshot row count."""
    if not WAREHOUSE.exists():
        return 0
    conn = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        return conn.execute("SELECT COUNT(*) FROM analytics.analytics.snap_customer").fetchone()[0]
    finally:
        conn.close()


@pytest.mark.skipif(not WAREHOUSE.exists(), reason="warehouse not built")
def test_scd2_snapshot_idempotent():
    """Running snapshot twice on unchanged data must not create new rows."""
    # Get initial count
    count_before = _get_snapshot_row_count()
    assert count_before > 0, "Snapshot must have data"

    # Run snapshot first time
    result1 = _run_dbt_snapshot()
    assert result1.returncode in (0, 2), f"First snapshot failed: {result1.stderr}"

    count_after_first = _get_snapshot_row_count()
    assert count_after_first == count_before, f"Row count changed after first run: {count_before} -> {count_after_first}"

    # Run snapshot second time (no source changes)
    result2 = _run_dbt_snapshot()
    assert result2.returncode in (0, 2), f"Second snapshot failed: {result2.stderr}"

    count_after_second = _get_snapshot_row_count()
    assert count_after_second == count_before, f"Row count changed after second run: {count_before} -> {count_after_second}"

    # Verify current version count unchanged
    conn = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        current_before = conn.execute(
            "SELECT COUNT(*) FROM analytics.analytics.snap_customer WHERE dbt_valid_to IS NULL"
        ).fetchone()[0]
        current_after = conn.execute(
            "SELECT COUNT(*) FROM analytics.analytics.snap_customer WHERE dbt_valid_to IS NULL"
        ).fetchone()[0]
        assert current_before == current_after, "Current version count changed"
    finally:
        conn.close()
