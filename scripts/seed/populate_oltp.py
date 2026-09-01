"""Load generated OLTP CSVs into Postgres as the simulated transactional source.

Creates the source_oltp schema, a least-privilege reader role, and COPY-loads
data/seed/oltp/*.csv. Uses admin credentials from env (never the reader).
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ingestion.envfile import load_dotenv

TABLES = {
    "order_items": ["item_id", "order_id", "product_id", "quantity", "unit_price_cents", "updated_at"],
    "payments": ["payment_id", "order_id", "amount_cents", "status", "method", "event_ts", "updated_at"],
    "inventory_levels": ["product_id", "warehouse_id", "stock_on_hand", "reorder_point", "updated_at"],
}


def admin_dsn() -> str:
    return (
        f"host={os.environ.get('SOURCE_PG_HOST', 'localhost')} "
        f"port={os.environ.get('SOURCE_PG_PORT', '5433')} "
        f"dbname={os.environ.get('SOURCE_PG_DB', 'sourcedb')} "
        f"user={os.environ.get('SOURCE_PG_ADMIN_USER', 'source_admin')} "
        f"password={os.environ.get('SOURCE_PG_ADMIN_PASSWORD', '')}"
    )


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop and recreate source tables")
    args = parser.parse_args()

    seed_dir = ROOT / "data" / "seed" / "oltp"
    if not seed_dir.exists():
        print("no seed files found; run scripts/seed/generate_sources.py first")
        return 1

    with psycopg.connect(admin_dsn()) as conn, conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS source_oltp")
        for table, columns in TABLES.items():
            if args.reset:
                cur.execute(f"DROP TABLE IF EXISTS source_oltp.{table} CASCADE")
            cols_ddl = ", ".join(
                f"{c} BIGINT" if c.endswith("_cents") or c in ("quantity", "stock_on_hand", "reorder_point")
                else (f"{c} TIMESTAMP" if c.endswith(("_at", "_ts")) else f"{c} TEXT")
                for c in columns
            )
            cur.execute(f"CREATE TABLE IF NOT EXISTS source_oltp.{table} ({cols_ddl})")
            cur.execute(f"TRUNCATE source_oltp.{table}")

            csv_path = seed_dir / f"{table}.csv"
            copy_stmt = (
                f"COPY source_oltp.{table} ({', '.join(columns)}) "
                f"FROM STDIN WITH (FORMAT csv, HEADER false)"
            )
            with cur.copy(copy_stmt) as copy:
                with csv_path.open("r", encoding="utf-8", newline="") as f:
                    next(f)
                    while chunk := f.read(1 << 20):
                        copy.write(chunk)
            count = cur.execute(f"SELECT COUNT(*) FROM source_oltp.{table}").fetchone()[0]
            print(f"{table}: {count} rows")

        cur.execute("DO $$ BEGIN"
                    " IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'source_reader') THEN"
                    " CREATE ROLE source_reader LOGIN PASSWORD 'change_me_source'; END IF; END $$;")
        cur.execute("GRANT USAGE ON SCHEMA source_oltp TO source_reader")
        cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA source_oltp TO source_reader")
        conn.commit()
    print("OLTP source ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
