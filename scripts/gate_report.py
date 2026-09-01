import os
import sys

sys.path.insert(0, '/opt/dataforge')
os.chdir('/opt/dataforge')
import duckdb

from ingestion.config import warehouse_path

conn = duckdb.connect(str(warehouse_path()), read_only=True)

print('=== RAW COUNTS (RDBMS included) ===')
for t in ['customers','regions','orders','returns','products','order_items','payments','inventory_levels']:
    c = conn.execute(f'SELECT COUNT(*) FROM raw.{t}').fetchone()[0]
    print(f'{t}: {c}')

print('=== WATERMARKS ===')
for r in conn.execute('SELECT source_name, watermark_value FROM raw.ingestion_watermarks ORDER BY 1').fetchall():
    print(r)

print('=== LINEAGE (per source) ===')
for r in conn.execute('SELECT source_name, run_mode, rows_extracted, rows_loaded, rows_quarantined FROM lineage.batch_lineage ORDER BY 1').fetchall():
    print(r)

print('=== DUPLICATE ORDER IDs PRESERVED IN RAW ===')
for r in conn.execute('SELECT order_id, COUNT(*) n FROM raw.orders GROUP BY 1 HAVING COUNT(*)>1 ORDER BY n DESC LIMIT 3').fetchall():
    print(r)

print('=== METADATA COLUMNS ON RDBMS RAW TABLES ===')
for t in ['order_items','payments','inventory_levels']:
    cols = conn.execute(f'SELECT column_name FROM information_schema.columns WHERE table_schema="raw" AND table_name="{t}" AND column_name LIKE "_source%"').fetchall()
    print(f'{t}: {[c[0] for c in cols]}')
