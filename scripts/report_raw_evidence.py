"""Print raw-layer evidence snapshot used in phase gate reports."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import duckdb

from ingestion.config import warehouse_path

conn = duckdb.connect(str(warehouse_path()), read_only=True)

print("=== RAW COUNTS ===")
for table in ["customers", "regions", "orders", "returns", "products"]:
    count = conn.execute(f"SELECT COUNT(*) FROM raw.{table}").fetchone()[0]
    print(f"{table}: {count}")

print("=== QUARANTINE (by reason) ===")
for table in ["orders", "returns", "customers", "products", "regions"]:
    rows = conn.execute(
        f"SELECT reason, COUNT(*) FROM raw.quarantine_{table} GROUP BY 1"
    ).fetchall()
    if rows:
        print(f"{table}: {rows}")

print("=== WATERMARKS ===")
for row in conn.execute(
    "SELECT source_name, watermark_value FROM raw.ingestion_watermarks ORDER BY 1"
).fetchall():
    print(row)

print("=== LINEAGE (per source) ===")
for row in conn.execute(
    """
    SELECT source_name, run_mode, rows_extracted, rows_loaded, rows_quarantined
    FROM lineage.batch_lineage ORDER BY source_name
    """
).fetchall():
    print(row)

print("=== DUPLICATE ORDER IDS PRESERVED IN RAW (I-02 fidelity) ===")
dupes = conn.execute(
    "SELECT order_id, COUNT(*) n FROM raw.orders GROUP BY 1 HAVING COUNT(*) > 1 "
    "ORDER BY n DESC LIMIT 3"
).fetchall()
print(dupes)

print("=== PRODUCTS V2 DRIFT: brand populated? (I-05) ===")
print(conn.execute(
    "SELECT brand IS NOT NULL AS has_brand, COUNT(*) FROM raw.products GROUP BY 1"
).fetchall())

print("=== CATEGORY CASING VARIANTS (I-07) ===")
for row in conn.execute(
    "SELECT category, COUNT(*) FROM raw.products GROUP BY 1 ORDER BY 2 DESC LIMIT 6"
).fetchall():
    print(row)
