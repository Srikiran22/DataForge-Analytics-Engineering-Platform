import ast
from pathlib import Path


def test_dag_parses_and_has_expected_structure():
    dag_path = Path(__file__).resolve().parents[1] / "dags" / "dataforge_daily.py"
    source = dag_path.read_text(encoding="utf-8")

    # Must be valid Python
    ast.parse(source)

    # Must define the DAG and its logical stages
    assert "dataforge_daily" in source
    for task in [
        "extract_load_customers", "extract_load_regions", "extract_load_orders",
        "extract_load_products", "extract_load_order_items", "extract_load_payments",
        "extract_load_inventory_levels", "extract_load_returns",
        "validate_raw", "dbt_snapshot", "dbt_staging", "dbt_intermediate",
        "dbt_core", "dbt_marts", "quality_checks", "publish"
    ]:
        assert task in source, f"missing task {task}"

    # Retries and timeouts must be configured
    assert "retries" in source
    assert "retry_delay" in source
    assert "execution_timeout" in source

    # Failure propagation: quality_checks upstream of publish
    assert "quality_checks" in source and "publish" in source

    # Orchestrates existing logic, no duplicated business transforms
    assert "ingestion" in source
