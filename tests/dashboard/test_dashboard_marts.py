from pathlib import Path

import duckdb
import pytest

APP = Path(__file__).resolve().parents[2] / "dashboards" / "app.py"
WAREHOUSE = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "analytics.duckdb"


def test_app_queries_only_marts_and_observability():
    src = APP.read_text(encoding="utf-8")
    # Direct guard: app.py must not contain forbidden relations outside of comments/asserts
    # So remove those two guard lines before checking
    for line in ["raw.", "main_staging.", "main_analytics.fct_", "main_analytics.dim_"]:
        # Count occurrences outside guard lines (which contain "must not query")
        count = 0
        for raw_line in src.splitlines():
            if "must not query" in raw_line:
                continue
            if line in raw_line.lower() and "from" in raw_line.lower():
                count += 1
        assert count == 0, f"app.py queries forbidden relation {line}"


def test_gross_revenue_matches_warehouse_truth():
    """Dashboard's gross revenue definition must equal mart_sales sum.

    Validates that mart_sales.gross_revenue equals the sum of total_amount_cents
    from fct_orders for delivered/shipped orders, computed independently.
    """
    if not WAREHOUSE.exists():
        pytest.skip("warehouse not built")
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    # Mart truth: sum of gross_revenue from mart_sales
    mart_sum = con.execute("SELECT sum(gross_revenue) FROM main_marts.mart_sales").fetchone()[0]
    # Independent computation from fact table (bypassing mart)
    fact_sum = con.execute("""
        SELECT sum(total_amount_cents) / 100.0
        FROM main_analytics.fct_orders
        WHERE status IN ('delivered', 'shipped')
    """).fetchone()[0]
    # Use approximate comparison for floating point
    assert abs(mart_sum - fact_sum) < 0.01, f"mart gross_revenue {mart_sum} != fact sum {fact_sum}"
    assert mart_sum > 0


def test_net_le_gross_everywhere():
    if not WAREHOUSE.exists():
        pytest.skip("warehouse not built")
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    bad = con.execute("SELECT count(*) FROM main_marts.mart_sales WHERE net_revenue > gross_revenue").fetchone()[0]
    assert bad == 0


def test_product_performance_no_duplicate_revenue_def():
    # Only one place defines product_revenue: mart_product_performance.sql
    mart_sql = (Path(__file__).resolve().parents[2] / "dbt" / "models" / "marts" / "product_performance" / "mart_product_performance.sql").read_text()
    inventory_sql = (Path(__file__).resolve().parents[2] / "dbt" / "models" / "marts" / "inventory" / "mart_inventory.sql").read_text()
    assert "product_revenue" not in inventory_sql
    assert mart_sql.count("product_revenue") >= 1


def test_freshness_panel_wired_to_real_state():
    if not WAREHOUSE.exists():
        pytest.skip("warehouse not built")
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    # obs_pipeline_runs must expose last_ingested_at that matches raw max(_ingested_at)
    obs = con.execute("SELECT last_ingested_at FROM main_observability.obs_pipeline_runs WHERE source_name='orders'").fetchone()
    assert obs is not None and obs[0] is not None
    raw_max = con.execute("SELECT max(_ingested_at) FROM raw.orders").fetchone()[0]
    assert obs[0] == raw_max


def test_app_has_staleness_flag_logic():
    src = APP.read_text(encoding="utf-8")
    assert "STALE_HOURS" in src
    assert "st.error" in src and "Stale" in src
    assert "st.success" in src and "fresh" in src.lower()
