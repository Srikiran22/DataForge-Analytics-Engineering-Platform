"""Connectivity probe for the RDBMS gate: reader role, real SELECT."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg

from ingestion.envfile import load_dotenv

load_dotenv()

dsn = (
    f"host={os.environ.get('SOURCE_PG_HOST', 'localhost')} "
    f"port={os.environ.get('SOURCE_PG_PORT', '5433')} "
    f"dbname=sourcedb user=source_reader password=change_me_source connect_timeout=5"
)

with psycopg.connect(dsn) as conn, conn.cursor() as cur:
    cur.execute("SELECT version()")
    print("connect OK:", cur.fetchone()[0][:44])
    cur.execute("SELECT COUNT(*) FROM source_oltp.order_items")
    print("reader SELECT order_items:", cur.fetchone()[0])
