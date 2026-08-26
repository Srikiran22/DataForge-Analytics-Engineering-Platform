"""Deterministic source-data generator.

Produces the six simulated sources with the imperfections documented in
docs/data_imperfections.md. Same config + same code => byte-identical output.

OLTP tables are written as CSV files under data/seed/oltp/ and loaded into
Postgres by populate_oltp.py, so generation never depends on a live database.
"""

import csv
import json
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ingestion.config import load_seed_config

STATUSES = ["placed", "shipped", "delivered", "cancelled"]
STATUS_WEIGHTS = [10, 20, 60, 10]
RETURN_REASONS = ["wrong_item", "damaged", "not_as_described", "better_price", "changed_mind"]
CATEGORY_POOL = ["electronics", "home_kitchen", "sports", "books", "fashion", "beauty", "toys", "grocery"]
CASING_VARIANTS = ["lower", "Title", "UPPER"]
BRANDS = ["Acme", "Globex", "Umbra", "Nordwind", "Kite&Co"]
SEGMENTS = ["consumer", "consumer", "consumer", "corporate"]
FIRST_NAMES = ["Ava", "Liam", "Noah", "Mia", "Ethan", "Zoe", "Ravi", "Sofia", "Jonas", "Leila", "Marc", "Ines"]
LAST_NAMES = ["Novak", "Silva", "Okafor", "Chen", "Duarte", "Kim", "Rossi", "Haddad", "Ford", "Meyer"]


def iso(dt_value: datetime) -> str:
    return dt_value.strftime("%Y-%m-%dT%H:%M:%SZ")


def daterange(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def bernoulli_count(rng: random.Random, n: int, pct: float) -> int:
    """Draw the number of affected records from per-record probability,
    honoring small percentages instead of truncating them away."""
    if n <= 0 or pct <= 0:
        return 0
    return sum(1 for _ in range(n) if rng.random() * 100 < pct)


def generate(cfg, out_root: Path):
    rng = random.Random(cfg.rng_seed)
    start = date.fromisoformat(cfg.start_date)
    end = date.fromisoformat(cfg.end_date)
    days = list(daterange(start, end))
    imp = cfg.imperfections

    out_source = out_root / "data" / "source"
    out_fixtures = out_root / "data" / "fixtures" / "products"
    out_oltp = out_root / "data" / "seed" / "oltp"
    for p in (out_source / "orders", out_source / "returns", out_fixtures, out_oltp):
        p.mkdir(parents=True, exist_ok=True)

    regions = [{"region_id": f"RG{i:02d}", "region_name": f"Region-{i:02d}", "country": c}
               for i, c in enumerate(["US", "US", "CA", "BR", "DE", "FR", "GB", "IN", "JP", "AU", "ZA", "MX"], start=1)]
    with (out_source / "regions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(regions[0]))
        w.writeheader()
        w.writerows(regions)

    n_customers = cfg.volumes["customers"]
    customers = []
    emails = []
    for i in range(1, n_customers + 1):
        cid = f"C{i:06d}"
        email = None if rng.random() * 100 < imp.get("missing_email_pct", 3.0) else f"user{i}@example.com"
        signup = start + timedelta(days=rng.randint(0, 180))
        signup_dt = datetime.combine(signup, datetime.min.time()).replace(
            hour=rng.randint(8, 22), minute=rng.randint(0, 59))
        customers.append({
            "customer_id": cid,
            "first_name": rng.choice(FIRST_NAMES),
            "last_name": rng.choice(LAST_NAMES),
            "email": email,
            "city": f"City-{rng.randint(1, 400)}",
            "region_id": rng.choice([r["region_id"] for r in regions]),
            "segment": rng.choice(SEGMENTS),
            "signup_date": signup.isoformat(),
            "updated_at": iso(signup_dt),
        })
        if email:
            emails.append(email)
    for c in customers:
        if c["email"] is None or rng.random() * 100 >= imp.get("duplicate_email_pct", 0.3):
            continue
        other_email = rng.choice(emails) if emails else None
        if other_email and other_email != c["email"]:
            c["email"] = other_email
    with (out_source / "customers.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(customers[0]))
        w.writeheader()
        w.writerows(customers)

    n_products = cfg.volumes["products"]
    products_v1, products_v2 = [], []
    for i in range(1, n_products + 1):
        pid = f"P{i:06d}"
        category = CATEGORY_POOL[(i - 1) % len(CATEGORY_POOL)]
        variant = CASING_VARIANTS[i % len(CASING_VARIANTS)]
        display_category = {"lower": category, "Title": category.capitalize(), "UPPER": category.upper()}[variant]
        price_cents = int(min(500000, max(100, abs(rng.gauss(60000, 45000)))))
        base = {
            "product_id": pid,
            "name": f"{display_category.replace('_', ' ').title()} Item {i}",
            "category": display_category,
            "price_cents": price_cents,
            "active": "true" if rng.random() > 0.05 else "false",
        }
        products_v1.append(dict(base))
        v2 = dict(base)
        v2["brand"] = BRANDS[i % len(BRANDS)]
        products_v2.append(v2)
    (out_fixtures / "v1.json").write_text(json.dumps(products_v1, indent=0), encoding="utf-8")
    (out_fixtures / "v2.json").write_text(json.dumps(products_v2, indent=0), encoding="utf-8")

    product_ids = [p["product_id"] for p in products_v1]
    product_price = {p["product_id"]: p["price_cents"] for p in products_v1}

    customer_ids = [c["customer_id"] for c in customers]
    order_seq = 0
    item_seq = 0
    payment_seq = 0
    return_seq = 0
    oltp_items = []
    oltp_payments = []
    inventory = []

    for wi, warehouse in enumerate(["WH-EAST", "WH-WEST", "WH-CENTRAL"], start=1):
        for pid in product_ids[wi % 3:: 3]:
            inventory.append({
                "product_id": pid, "warehouse_id": warehouse,
                "stock_on_hand": rng.randint(0, 900),
                "reorder_point": 60,
                "updated_at": iso(datetime.combine(end, datetime.min.time()).replace(
                    hour=rng.randint(0, 23), minute=rng.randint(0, 59))),
            })

    all_returns = []
    daily_orders_by_day = {}

    for day_index, day in enumerate(days):
        n_today = max(30, int(rng.gauss(cfg.volumes["orders_per_day_avg"], 45)))
        day_orders = []
        for _ in range(n_today):
            order_seq += 1
            oid = f"O{order_seq:07d}"
            ts = datetime.combine(day, datetime.min.time()).replace(
                hour=rng.randint(0, 23), minute=rng.randint(0, 59), second=rng.randint(0, 59))
            invalid_fk = rng.random() * 100 < imp.get("invalid_customer_fk_pct", 0.5)
            cust_id = (
                f"C{rng.randint(n_customers + 1, n_customers + 9999):06d}"
                if invalid_fk else rng.choice(customer_ids)
            )
            status = rng.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
            record = {
                "order_id": oid,
                "customer_id": cust_id,
                "order_ts": iso(ts),
                "status": status,
                "total_amount_cents": 0,
                "currency": "USD",
                "updated_at": iso(ts),
            }

            n_items = max(1, min(6, int(rng.expovariate(1.0 / cfg.volumes["items_per_order_avg"])) + 1))
            total = 0
            for _ in range(n_items):
                item_seq += 1
                pid = rng.choice(product_ids)
                qty = rng.randint(1, 4)
                unit_price = product_price[pid]
                roll = rng.random() * 100
                if roll < imp.get("price_outlier_pct", 0.1):
                    unit_price = 0 if rng.random() < 0.5 else unit_price * 25
                total += qty * unit_price
                updated = ts + timedelta(minutes=rng.randint(1, 120))
                oltp_items.append({
                    "item_id": f"I{item_seq:08d}", "order_id": oid, "product_id": pid,
                    "quantity": qty, "unit_price_cents": unit_price,
                    "updated_at": iso(updated),
                })
                if status == "delivered" and rng.random() < cfg.volumes["returns_rate"]:
                    return_seq += 1
                    ret_ts = min(ts + timedelta(days=rng.randint(2, 20)),
                                 datetime.combine(end, datetime.max.time()))
                    all_returns.append({
                        "return_id": f"R{return_seq:07d}",
                        "order_item_id": f"I{item_seq:08d}",
                        "returned_at": iso(ret_ts),
                        "reason": rng.choice(RETURN_REASONS),
                        "quantity": 1,
                        "updated_at": iso(ret_ts),
                    })

            record["total_amount_cents"] = total

            payment_seq += 1
            is_late = rng.random() * 100 < imp.get("late_payment_pct", 2.0)
            pay_updated = (
                ts + timedelta(days=rng.randint(3, 7)) if is_late
                else ts + timedelta(hours=rng.randint(1, 12))
            )
            pay_updated = min(pay_updated, datetime.combine(end, datetime.max.time()))
            oltp_payments.append({
                "payment_id": f"PM{payment_seq:08d}", "order_id": oid,
                "amount_cents": total, "status": "settled" if status != "cancelled" else "failed",
                "method": rng.choice(["card", "paypal", "bank_transfer"]),
                "event_ts": iso(ts), "updated_at": iso(pay_updated),
            })

            day_orders.append(record)

        replayed_exact, replayed_mutated = [], []
        replay_n = bernoulli_count(rng, len(day_orders), imp.get("order_replay_pct", 1.0))
        if replay_n and day_index > 0:
            sample = rng.sample(day_orders, min(replay_n, len(day_orders)))
            half = len(sample) // 2
            replayed_exact = list(sample[:half])
            for rec in sample[half:]:
                mutated = dict(rec)
                original_ts = datetime.strptime(rec["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
                mutated["updated_at"] = iso(original_ts + timedelta(minutes=90))
                mutated["total_amount_cents"] = str(int(rec["total_amount_cents"]) + 137)
                replayed_mutated.append(mutated)

        file_records = list(day_orders) + replayed_exact + replayed_mutated
        malformed_n = bernoulli_count(rng, len(file_records), imp.get("malformed_line_pct", 0.2))
        corrupt_indexes = set(rng.sample(range(len(file_records)), malformed_n)) if malformed_n else set()

        path = out_source / "orders" / f"dt={day.isoformat()}.ndjson"
        with path.open("w", encoding="utf-8") as f:
            for idx, rec in enumerate(file_records):
                line = json.dumps(rec, separators=(",", ":"))
                if idx in corrupt_indexes:
                    cut = max(10, len(line) // 2)
                    f.write(line[:cut] + "\n")
                else:
                    f.write(line + "\n")

        daily_orders_by_day[day] = len(file_records)

    returns_by_day = {}
    for ret in all_returns:
        day = ret["returned_at"][:10]
        returns_by_day.setdefault(day, []).append(ret)
    for day_str, recs in sorted(returns_by_day.items()):
        file_records = list(recs)
        malformed_n = bernoulli_count(rng, len(file_records), imp.get("malformed_line_pct", 0.2))
        corrupt = set(rng.sample(range(len(file_records)), malformed_n)) if malformed_n else set()
        path = out_source / "returns" / f"dt={day_str}.ndjson"
        with path.open("w", encoding="utf-8") as f:
            for idx, rec in enumerate(file_records):
                line = json.dumps(rec, separators=(",", ":"))
                f.write((line[:max(10, len(line) // 2)] + "\n") if idx in corrupt else line + "\n")

    def write_oltp_csv(name, rows):
        if not rows:
            (out_oltp / f"{name}.csv").write_text("", encoding="utf-8")
            return
        with (out_oltp / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    write_oltp_csv("order_items", oltp_items)
    write_oltp_csv("payments", oltp_payments)
    write_oltp_csv("inventory_levels", inventory)

    summary = {
        "customers": len(customers),
        "regions": len(regions),
        "products_fixture_v1": len(products_v1),
        "products_fixture_v2": len(products_v2),
        "orders_total_including_replay_and_corrupt": sum(daily_orders_by_day.values()),
        "order_items": len(oltp_items),
        "payments": len(oltp_payments),
        "returns": len(all_returns),
        "inventory_levels": len(inventory),
        "date_window_days": len(days),
    }
    (out_oltp.parent / "seed_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    override = None
    if len(sys.argv) > 1:
        override = Path(sys.argv[1])
    generate(load_seed_config(), ROOT if override is None else override)
