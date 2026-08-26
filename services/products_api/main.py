"""Mock products API serving versioned fixture files.

Serves /products from data/fixtures/products/v{N}.json chosen by date:
requests before the drift date get v1 (no `brand`), after it get v2.
`?fail=500` simulates outages; `?fail=flaky` fails twice then succeeds,
exercising retry logic end-to-end for reliability tests.
"""

import json
import os
from datetime import UTC, datetime
from datetime import date as date_cls
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="products-mock")

FIXTURE_DIR = Path(
    os.environ.get(
        "PRODUCTS_FIXTURE_DIR",
        Path(__file__).resolve().parents[2] / "data" / "fixtures" / "products",
    )
)
V2_FROM = os.environ.get("PRODUCTS_V2_FROM", "2026-02-01")


def select_fixture(fixture_dir: Path, v2_from: str, today: date_cls) -> tuple[str, list]:
    cutoff = date_cls.fromisoformat(v2_from)
    version = 2 if today >= cutoff else 1
    path = fixture_dir / f"v{version}.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"fixture missing: {path}")
    return f"v{version}", json.loads(path.read_text(encoding="utf-8"))


@app.get("/products")
def products(request: Request):
    fail_mode = request.query_params.get("fail")
    if fail_mode == "500":
        raise HTTPException(status_code=500, detail="simulated outage")
    if fail_mode == "flaky":
        hits = getattr(request.app.state, "flaky_hits", 0) + 1
        request.app.state.flaky_hits = hits
        if hits <= 2:
            raise HTTPException(status_code=503, detail="simulated flake")

    version, payload = select_fixture(FIXTURE_DIR, V2_FROM, datetime.now(UTC).date())
    return JSONResponse(content=payload, headers={"X-Fixture-Version": version})


@app.get("/health")
def health():
    return {"status": "ok"}
