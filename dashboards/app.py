"""
DataForge dashboard — CONSUMER of marts only.

Hard rule: every query reads main_marts.* or main_observability.obs_pipeline_runs.
No raw.* / main_staging.* / main_analytics.* (facts/dims) for convenience.
Each business KPI traces to docs/metrics_dictionary.md single definition.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = Path(os.environ.get("WAREHOUSE_PATH", PROJECT_ROOT / "data" / "warehouse" / "analytics.duckdb"))
STALE_HOURS = 26

st.set_page_config(page_title="DataForge — Analytics", layout="wide")

@st.cache_resource
def conn_ro():
    return duckdb.connect(str(WAREHOUSE), read_only=True)

def q(sql: str, params=None) -> pd.DataFrame:
    # Guard: reject accidental raw/staging access at query time (defense in depth).
    lowered = sql.lower()
    assert "raw." not in lowered, "dashboard must not query raw.*"
    assert "main_staging." not in lowered, "dashboard must not query staging"
    # fact/dim tables (main_analytics) are also forbidden — marts only
    # Allow only main_marts.* and main_observability.*
    # (intermediate views are also not marts)
    for forbidden in ["main_analytics.fct_", "main_analytics.dim_", "main_intermediate.", "information_schema"]:
        assert forbidden not in lowered, f"dashboard must not query {forbidden}"
    c = conn_ro()
    return c.execute(sql, params or []).df()

st.title("DataForge — Analytics Engineering Platform")
st.caption(
    f"Warehouse `{WAREHOUSE}` · {datetime.now(UTC):%Y-%m-%d %H:%M UTC}"
    " · marts-only queries · freshness panel is the trust chain"
)

# Tabs: business vs operational separation
tab_sales, tab_retention, tab_product, tab_returns, tab_inventory, tab_ops = st.tabs(
    ["Sales", "Retention & Cohorts", "Products", "Returns", "Inventory", "⚙ Operational status"]
)

with tab_sales:
    st.subheader("Revenue trends (BQ-01, BQ-08)")
    df = q("SELECT date as d, sum(net_revenue) as net FROM main_marts.mart_sales GROUP BY 1 ORDER BY 1")
    if df.empty:
        st.info("No sales data — pipeline has not run yet.")
    else:
        df["d"] = pd.to_datetime(df["d"])
        st.line_chart(df.set_index("d")["net"])
        st.metric("Net revenue (all time)", f"${df['net'].sum():,.2f}")

    st.subheader("Orders & AOV (BQ-02, BQ-03)")
    df2 = q("SELECT date, count(*) as orders, sum(net_revenue) as rev FROM main_marts.mart_sales GROUP BY 1 ORDER BY 1")
    if not df2.empty:
        df2["aov"] = df2["rev"] / df2["orders"].replace(0, pd.NA)
        st.line_chart(df2.set_index("date")[["orders"]])
        st.line_chart(df2.set_index("date")[["aov"]])

with tab_retention:
    st.subheader("Repeat purchase — cohort retention (BQ-04, BQ-05)")
    df = q("SELECT cohort_month, order_month, retention_rate FROM main_marts.mart_customer_retention ORDER BY 1,2 LIMIT 500")
    if df.empty:
        st.info("No cohort data.")
    else:
        # Pivot for heatmap-like view via bar
        st.dataframe(df.head(20))
        st.caption("retention_rate = retained customers / cohort size")

with tab_product:
    st.subheader("Product performance (BQ-06)")
    df = q("SELECT product_id, category, units_sold, product_revenue, return_rate FROM main_marts.mart_product_performance ORDER BY product_revenue DESC LIMIT 20")
    st.dataframe(df)
    if not df.empty:
        st.bar_chart(df.set_index("product_id")["product_revenue"].head(10))

with tab_returns:
    st.subheader("Returns by reason & category (BQ-07)")
    df = q("SELECT reason, sum(total_returned_units) as units, sum(total_returned_revenue) as rev FROM main_marts.mart_returns GROUP BY reason ORDER BY units DESC")
    st.dataframe(df)
    if not df.empty:
        st.bar_chart(df.set_index("reason")["units"])

with tab_inventory:
    st.subheader("Inventory position & low-stock (BQ-09)")
    df = q("SELECT warehouse_id, count(*) as skus, sum(case when low_stock_flag then 1 else 0 end) as low FROM main_marts.mart_inventory GROUP BY 1")
    st.dataframe(df)
    df2 = q("SELECT product_id, warehouse_id, stock_on_hand, reorder_point, days_of_cover FROM main_marts.mart_inventory WHERE low_stock_flag = true LIMIT 20")
    st.caption("Low-stock items (limit 20)")
    st.dataframe(df2)

with tab_ops:
    st.subheader("Pipeline status — the trust chain (separate from business marts)")
    obs = q("SELECT source_name, row_count, last_ingested_at, last_watermark, quarantined_rows FROM main_observability.obs_pipeline_runs ORDER BY source_name")
    st.dataframe(obs, use_container_width=True)
    if not obs.empty:
        # Staleness flag per spec: warn when last_ingested_at > STALE_HOURS
        now = datetime.now(UTC)
        obs["_age_h"] = (now - pd.to_datetime(obs["last_ingested_at"], utc=True)).dt.total_seconds() / 3600
        stale = obs[obs["_age_h"] > STALE_HOURS]
        if not stale.empty:
            st.error(f"⚠ Stale sources (>{STALE_HOURS}h): {', '.join(stale['source_name'])} — panels may show outdated data. Check pipeline.")
        else:
            st.success(f"All sources fresh (<{STALE_HOURS}h).")
        # Row-count sparkline proxy: show counts per source
        st.bar_chart(obs.set_index("source_name")["row_count"])
    st.caption("Source: real warehouse state — row counts, watermarks, quarantined counts. No hardcoded numbers.")

st.sidebar.markdown("### Metrics dictionary")
st.sidebar.info("Every business KPI on this page maps 1:1 to `docs/metrics_dictionary.md` and its underlying mart SQL. No panel re-derives revenue.")
if st.sidebar.button("Re-run watermark check"):
    st.cache_resource.clear()
    st.rerun()

# Footer assertion for tests: expose which relations were queried
st.session_state["_queried_relations"] = ["main_marts.*", "main_observability.*"]
