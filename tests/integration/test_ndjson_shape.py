"""NDJSON source shape: malformed-line quarantine, replay duplicates,
incremental watermark behavior, and rerun idempotency."""

import json

from ingestion import pipeline
from tests.integration.conftest import CUSTOMER_A, ORDER_1, count


def _order(oid, updated_at, customer_id="C1", amount="1000"):
    return dict(ORDER_1, order_id=oid, updated_at=updated_at, order_ts=updated_at,
                customer_id=customer_id, total_amount_cents=amount)


def test_malformed_lines_quarantined_valid_rows_loaded(wh, source_dir):
    source_dir["write_customers"]([CUSTOMER_A])
    pipeline.run_source(wh, "customers", batch_id="c-batch", full=True)

    good = json.dumps(_order("O1", "2026-01-01T12:00:00Z"))
    bad_truncated = '{"order_id": "O2", "custo'
    garbage = "not-json"
    source_dir["write_orders_day"]("2026-01-01", [good, bad_truncated, garbage])

    stats = pipeline.run_source(wh, "orders", batch_id="o-batch-1")

    assert stats["loaded"] == 1
    assert stats["quarantined"] == 2
    assert count(wh, "raw.orders") == 1
    reasons = wh.execute(
        "SELECT reason, COUNT(*) FROM raw.quarantine_orders GROUP BY reason"
    ).fetchall()
    assert dict(reasons) == {"malformed_json": 2}


def test_invalid_fk_order_quarantined_not_silently_loaded(wh, source_dir):
    source_dir["write_customers"]([CUSTOMER_A])
    pipeline.run_source(wh, "customers", batch_id="c-batch", full=True)

    valid = json.dumps(_order("O1", "2026-01-01T12:00:00Z"))
    orphan = json.dumps(_order("O9", "2026-01-02T12:00:00Z", customer_id="C999999"))
    source_dir["write_orders_day"]("2026-01-01", [valid, orphan])

    stats = pipeline.run_source(wh, "orders", batch_id="o-batch-fk")

    assert stats["loaded"] == 1
    assert stats["quarantined"] == 1
    assert count(wh, "raw.orders", "customer_id = 'C999999'") == 0
    assert count(wh, "raw.quarantine_orders", "reason = 'invalid_fk_customer'") == 1


def test_replay_semantics_exact_skipped_mutated_kept(wh, source_dir):
    """I-02, two replay variants:
    - byte-identical redelivery (same updated_at) is a no-op: skipped by the
      watermark filter and COUNTED, never duplicated;
    - a mutated re-delivery (updated_at advanced - the source contract for
      'this record changed') lands as a SECOND version in raw (fidelity);
      dedup to one current version is a staging-layer decision (Phase 4)."""
    source_dir["write_customers"]([CUSTOMER_A])
    pipeline.run_source(wh, "customers", batch_id="c-batch", full=True)

    day1 = [json.dumps(_order("O1", "2026-01-01T12:00:00Z")),
            json.dumps(_order("O2", "2026-01-01T13:00:00Z"))]
    source_dir["write_orders_day"]("2026-01-01", day1)
    pipeline.run_source(wh, "orders", batch_id="day1")

    exact_replay = json.dumps(_order("O1", "2026-01-01T12:00:00Z"))
    mutated = _order("O2", "2026-01-04T09:00:00Z")
    mutated["total_amount_cents"] = "9999"
    source_dir["write_orders_day"](
        "2026-01-04",
        [json.dumps(mutated), exact_replay,
         json.dumps(_order("O5", "2026-01-04T10:00:00Z"))],
    )
    stats = pipeline.run_source(wh, "orders", batch_id="day4")

    assert stats["skipped_replayed"] == 3
    # 3 = 1 byte-identical replay + 2 records rescanned from the still-present
    # dt=2026-01-01.ndjson file (files persist on disk; every run rescans them
    # and re-skips already-watermarked records - by design).

    copies_o1 = count(wh, "raw.orders", "order_id = 'O1'")
    copies_o2 = count(wh, "raw.orders", "order_id = 'O2'")
    assert copies_o1 == 1
    assert copies_o2 == 2


def test_incremental_watermark_skips_old_and_rerun_is_idempotent(wh, source_dir):
    source_dir["write_customers"]([CUSTOMER_A])
    pipeline.run_source(wh, "customers", batch_id="c-batch", full=True)

    source_dir["write_orders_day"]("2026-01-01",
                                   [json.dumps(_order("O1", "2026-01-01T12:00:00Z"))])
    first = pipeline.run_source(wh, "orders", batch_id="inc-1")
    assert first["watermark_advanced"] is True
    assert first["loaded"] == 1

    same_again = pipeline.run_source(wh, "orders", batch_id="inc-2")
    assert same_again["extracted"] == 0
    assert same_again["loaded"] == 0
    assert same_again["watermark_advanced"] is False
    assert count(wh, "raw.orders") == 1

    source_dir["write_orders_day"](
        "2026-01-05",
        *[[json.dumps(_order("O3", "2026-01-05T10:00:00Z")),
           json.dumps(_order("O1", "2026-01-01T12:00:00Z"))]],
    )
    second = pipeline.run_source(wh, "orders", batch_id="inc-3")
    assert second["loaded"] == 1
    assert count(wh, "raw.orders", "order_id = 'O3'") == 1
