import duckdb

conn = duckdb.connect("data/warehouse/analytics.duckdb", read_only=True)
query = """
    SELECT table_catalog, table_schema, table_name
    FROM information_schema.tables
    WHERE table_name = 'snap_customer'
"""
print(conn.execute(query).fetchall())
conn.close()
