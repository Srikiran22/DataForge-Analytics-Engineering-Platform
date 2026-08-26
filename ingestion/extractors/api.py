import time
from collections.abc import Callable

import httpx

from ingestion.extractors.retry import TransientAPIError, classify_status, with_retry


def fetch_products(
    base_url: str,
    client: httpx.Client | None = None,
    max_attempts: int = 4,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict]:
    """Fetch the full product snapshot from the mock API with retry/backoff."""
    own_client = client is None
    client = client or httpx.Client(timeout=10.0)

    def _get() -> list[dict]:
        try:
            response = client.get(f"{base_url.rstrip('/')}/products")
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            raise TransientAPIError(f"transport failure: {exc}") from exc
        if classify_status(response.status_code):
            raise TransientAPIError(f"transient HTTP {response.status_code}")
        if response.status_code != 200:
            response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("products endpoint must return a JSON array")
        return payload

    try:
        return with_retry(_get, max_attempts=max_attempts, sleep=sleep)
    finally:
        if own_client:
            client.close()
