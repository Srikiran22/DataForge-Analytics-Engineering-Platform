import duckdb

conn = duckdb.connect('/opt/dataforge/data/warehouse/analytics.duckdb', read_only=True)
for t in ['order_items','payments','inventory_levels']:
    cols = conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='raw' AND table_name=? AND column_name LIKE '_source%'", [t]).fetchall()
    print(f'{t}: {[c[0] for c in cols]}')
