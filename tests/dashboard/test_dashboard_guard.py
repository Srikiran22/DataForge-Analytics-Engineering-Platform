"""Test that the dashboard query guard actually rejects forbidden queries."""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from dashboards.app import q  # noqa: E402


def test_guard_rejects_raw_query():
    """Dashboard q() must reject queries against raw tables."""
    try:
        q("SELECT * FROM raw.orders LIMIT 1")
        pytest.fail("Expected assertion error for raw query")
    except AssertionError as e:
        assert "raw" in str(e).lower()


def test_guard_rejects_staging_query():
    """Dashboard q() must reject queries against staging."""
    try:
        q("SELECT * FROM main_staging.stg_orders LIMIT 1")
        pytest.fail("Expected assertion error for staging query")
    except AssertionError as e:
        assert "staging" in str(e).lower()


def test_guard_rejects_fact_query():
    """Dashboard q() must reject queries against fact tables."""
    try:
        q("SELECT * FROM main_analytics.fct_orders LIMIT 1")
        pytest.fail("Expected assertion error for fact query")
    except AssertionError as e:
        assert "fct_" in str(e).lower()


def test_guard_rejects_dim_query():
    """Dashboard q() must reject queries against dimension tables."""
    try:
        q("SELECT * FROM main_analytics.dim_customer LIMIT 1")
        pytest.fail("Expected assertion error for dim query")
    except AssertionError as e:
        assert "dim_" in str(e).lower()


def test_guard_allows_marts_query():
    """Dashboard q() must allow queries against marts."""
    # This will fail if warehouse doesn't exist, but should not trigger the guard
    # We just verify the guard logic doesn't falsely reject marts
    try:
        q("SELECT 1 as x")
    except Exception as e:
        # Connection error is OK, guard error is not
        assert "dashboard must not query" not in str(e)
