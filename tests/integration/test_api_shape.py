"""API source shape: retry/backoff, fixture version selection (I-05 drift),
and failure propagation after exhausted retries."""

import json
from datetime import date

import httpx
import pytest

from ingestion.extractors import api as api_extractor
from services.products_api.main import select_fixture

FIXTURES = [
    {"product_id": "P1", "name": "Widget", "category": "electronics",
     "price_cents": 1999, "active": "true"},
    {"product_id": "P2", "name": "Gadget", "category": "Electronics",
     "price_cents": 2999, "active": "false", "brand": "Acme"},
]


def test_transient_500s_are_retried_then_succeed():
    calls = {"n": 0}
    statuses = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            statuses.append(500)
            return httpx.Response(500, json={"detail": "simulated"})
        statuses.append(200)
        return httpx.Response(200, json=FIXTURES)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    sleeps = []
    rows = api_extractor.fetch_products(
        "http://testserver", client=client, max_attempts=4,
        sleep=lambda s: sleeps.append(s),
    )

    assert rows == FIXTURES
    assert statuses == [500, 500, 200]
    assert sleeps == [0.5, 1.0]
    client.close()


def test_permanent_failure_raises_after_exhausting_retries():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    sleeps = []
    with pytest.raises(api_extractor.TransientAPIError):
        api_extractor.fetch_products(
            "http://testserver", client=client, max_attempts=3,
            sleep=sleeps.append,
        )
    assert sleeps == [0.5, 1.0]
    client.close()


def test_404_is_not_retried():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        api_extractor.fetch_products("http://testserver", client=client, max_attempts=3)
    client.close()


def test_v2_fixture_adds_brand_column(tmp_path):
    """I-05: schema drift = new column appears in API v2."""
    v1_payload = [{"product_id": "P1", "name": "W", "category": "electronics",
                   "price_cents": 1999, "active": "true"}]
    v2_payload = [dict(v1_payload[0], brand="Acme")]
    (tmp_path / "v1.json").write_text(json.dumps(v1_payload), encoding="utf-8")
    (tmp_path / "v2.json").write_text(json.dumps(v2_payload), encoding="utf-8")

    before_drift = select_fixture(tmp_path, "2026-02-01", date(2026, 1, 31))
    on_drift_day = select_fixture(tmp_path, "2026-02-01", date(2026, 2, 1))

    assert before_drift[0] == "v1"
    assert "brand" not in before_drift[1][0]
    assert on_drift_day[0] == "v2"
    assert on_drift_day[1][0]["brand"] == "Acme"


def test_missing_fixture_fails_loudly(tmp_path):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        select_fixture(tmp_path / "does-not-exist", "2026-02-01", date(2026, 2, 2))
