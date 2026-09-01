import json
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ingestion import pipeline
from ingestion.envfile import load_dotenv

load_dotenv()


@pytest.fixture()
def wh(tmp_path):
    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    pipeline.init_warehouse(conn)
    yield conn
    conn.close()


@pytest.fixture()
def source_dir(tmp_path, monkeypatch):
    """Redirect data/source to a temp dir with tiny fixtures."""
    src = tmp_path / "data" / "source"
    (src / "orders").mkdir(parents=True)
    (src / "returns").mkdir(parents=True)
    monkeypatch.setenv("DATA_SOURCE_ROOT", str(src))

    def write_customers(rows):
        header = "customer_id,first_name,last_name,email,city,region_id,segment,signup_date,updated_at"
        lines = [header]
        for r in rows:
            lines.append(",".join(str(r.get(k, "")) for k in [
                "customer_id", "first_name", "last_name", "email", "city",
                "region_id", "segment", "signup_date", "updated_at"]))
        (src / "customers.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_orders_day(day, records_and_raw):
        p = src / "orders" / f"dt={day}.ndjson"
        p.write_text("".join(line + "\n" for line in records_and_raw), encoding="utf-8")

    def write_returns_day(day, records):
        p = src / "returns" / f"dt={day}.ndjson"
        p.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")

    return {
        "path": src,
        "write_customers": write_customers,
        "write_orders_day": write_orders_day,
        "write_returns_day": write_returns_day,
    }


def count(conn, table, where="1=1"):
    return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]


CUSTOMER_A = {"customer_id": "C1", "first_name": "A", "last_name": "B", "email": "a@x.com",
              "city": "X", "region_id": "RG01", "segment": "consumer",
              "signup_date": "2024-09-01", "updated_at": "2024-09-01T10:00:00Z"}
ORDER_1 = {"order_id": "O1", "customer_id": "C1", "order_ts": "2026-01-01T12:00:00Z",
           "status": "delivered", "total_amount_cents": "1000", "currency": "USD",
           "updated_at": "2026-01-01T12:00:00Z"}
