from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpec:
    name: str
    shape: str                    # csv | ndjson | api | rdbms
    natural_key: tuple[str, ...]  # record-level duplicate detection key
    watermark_field: str | None
    raw_table: str
    quarantine_table: str


SOURCES: dict[str, SourceSpec] = {
    "customers": SourceSpec(
        name="customers", shape="csv",
        natural_key=("customer_id",), watermark_field=None,
        raw_table="raw.customers", quarantine_table="raw.quarantine_customers",
    ),
    "regions": SourceSpec(
        name="regions", shape="csv",
        natural_key=("region_id",), watermark_field=None,
        raw_table="raw.regions", quarantine_table="raw.quarantine_regions",
    ),
    "orders": SourceSpec(
        name="orders", shape="ndjson",
        natural_key=("order_id",), watermark_field="updated_at",
        raw_table="raw.orders", quarantine_table="raw.quarantine_orders",
    ),
    "returns": SourceSpec(
        name="returns", shape="ndjson",
        natural_key=("return_id",), watermark_field="returned_at",
        raw_table="raw.returns", quarantine_table="raw.quarantine_returns",
    ),
    "products": SourceSpec(
        name="products", shape="api",
        natural_key=("product_id",), watermark_field=None,
        raw_table="raw.products", quarantine_table="raw.quarantine_products",
    ),
    "order_items": SourceSpec(
        name="order_items", shape="rdbms",
        natural_key=("item_id",), watermark_field="updated_at",
        raw_table="raw.order_items", quarantine_table=None,
    ),
    "payments": SourceSpec(
        name="payments", shape="rdbms",
        natural_key=("payment_id",), watermark_field="updated_at",
        raw_table="raw.payments", quarantine_table=None,
    ),
    "inventory_levels": SourceSpec(
        name="inventory_levels", shape="rdbms",
        natural_key=("product_id", "warehouse_id"), watermark_field="updated_at",
        raw_table="raw.inventory_levels", quarantine_table=None,
    ),
}

INGESTION_METADATA_COLUMNS = [
    ("_source_name", "VARCHAR"),
    ("_batch_id", "VARCHAR"),
    ("_ingested_at", "TIMESTAMP"),
    ("_source_file", "VARCHAR"),
    ("_source_row_number", "BIGINT"),
]

RAW_VALUE_TYPE = "VARCHAR"
