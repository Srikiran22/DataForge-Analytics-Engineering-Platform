"""
DataForge daily pipeline: extract -> load_raw -> validate -> dbt
(snapshot->staging->intermediate->core->marts) -> quality -> publish

Business logic lives in ingestion/ and dbt/ -- the DAG only orchestrates.
Retries, timeouts, idempotency, and failure propagation are proven by tests.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from airflow import DAG

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE = PROJECT_ROOT / "data" / "warehouse" / "analytics.duckdb"

default_args = {
    "owner": "dataforge",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(seconds=10),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=20),
}

with DAG(
    dag_id="dataforge_daily",
    default_args=default_args,
    description="DataForge: ingestion -> raw -> dbt -> quality -> publish",
    schedule="@daily",
    start_date=datetime(2024, 9, 1),
    catchup=False,
    tags=["dataforge", "elt"],
    max_active_runs=1,
) as dag:

    def _run_ingestion(source: str):
        """Delegate to ingestion.pipeline -- no business logic here."""
        sys.path.insert(0, str(PROJECT_ROOT))
        from ingestion import pipeline
        from ingestion.envfile import load_dotenv
        load_dotenv()
        conn = pipeline.connect_warehouse()
        try:
            pipeline.init_warehouse(conn)
            stats = pipeline.run_source(conn, source)
            # Failure propagation: quarantine threshold check
            if stats.get("quarantined", 0) > 10000:
                raise ValueError(f"Quarantine threshold exceeded for {source}")
            return stats
        finally:
            conn.close()

    # Extract tasks for all sources
    extract_customers = PythonOperator(
        task_id="extract_load_customers",
        python_callable=lambda: _run_ingestion("customers"),
    )

    extract_regions = PythonOperator(
        task_id="extract_load_regions",
        python_callable=lambda: _run_ingestion("regions"),
    )

    extract_orders = PythonOperator(
        task_id="extract_load_orders",
        python_callable=lambda: _run_ingestion("orders"),
    )

    extract_products = PythonOperator(
        task_id="extract_load_products",
        python_callable=lambda: _run_ingestion("products"),
    )

    extract_order_items = PythonOperator(
        task_id="extract_load_order_items",
        python_callable=lambda: _run_ingestion("order_items"),
    )

    extract_payments = PythonOperator(
        task_id="extract_load_payments",
        python_callable=lambda: _run_ingestion("payments"),
    )

    extract_inventory_levels = PythonOperator(
        task_id="extract_load_inventory_levels",
        python_callable=lambda: _run_ingestion("inventory_levels"),
    )

    extract_returns = PythonOperator(
        task_id="extract_load_returns",
        python_callable=lambda: _run_ingestion("returns"),
    )

    dbt_cmd_prefix = f"cd {PROJECT_ROOT}/dbt && WAREHOUSE_PATH={WAREHOUSE}"

    validate_raw = BashOperator(
        task_id="validate_raw",
        bash_command=f"{dbt_cmd_prefix} dbt test --select source:raw --store-failures "
        f"2>&1 | tail -20; exit ${{PIPESTATUS[0]}}",
    )

    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"{dbt_cmd_prefix} dbt snapshot 2>&1 | tail -20; "
        f"exit ${{PIPESTATUS[0]}}",
    )

    dbt_staging = BashOperator(
        task_id="dbt_staging",
        bash_command=f"{dbt_cmd_prefix} dbt run --select staging 2>&1 | "
        f"tail -20; exit ${{PIPESTATUS[0]}}",
    )

    dbt_intermediate = BashOperator(
        task_id="dbt_intermediate",
        bash_command=f"{dbt_cmd_prefix} dbt run --select intermediate 2>&1 | "
        f"tail -20; exit ${{PIPESTATUS[0]}}",
    )

    dbt_core = BashOperator(
        task_id="dbt_core",
        bash_command=f"{dbt_cmd_prefix} dbt run --select core 2>&1 | "
        f"tail -20; exit ${{PIPESTATUS[0]}}",
    )

    dbt_marts = BashOperator(
        task_id="dbt_marts",
        bash_command=f"{dbt_cmd_prefix} dbt run --select marts 2>&1 | "
        f"tail -20; exit ${{PIPESTATUS[0]}}",
    )

    quality_checks = BashOperator(
        task_id="quality_checks",
        bash_command=f"{dbt_cmd_prefix} dbt test --select marts,core 2>&1 | "
        f"tail -30; exit ${{PIPESTATUS[0]}}",
    )

    publish = BashOperator(
        task_id="publish",
        bash_command=f'echo "publish: marts ready at {WAREHOUSE}"; '
        f"ls -lh {WAREHOUSE} | awk '{{print \\$5, \\$9}}'",
    )

    # Dependencies: extract (parallel) -> validate -> snapshot ->
    # staging -> intermediate -> core -> marts -> quality -> publish
    [
        extract_customers,
        extract_regions,
        extract_orders,
        extract_products,
        extract_order_items,
        extract_payments,
        extract_inventory_levels,
        extract_returns,
    ] >> validate_raw
    (
        validate_raw
        >> dbt_snapshot
        >> dbt_staging
        >> dbt_intermediate
        >> dbt_core
        >> dbt_marts
        >> quality_checks
        >> publish
    )
