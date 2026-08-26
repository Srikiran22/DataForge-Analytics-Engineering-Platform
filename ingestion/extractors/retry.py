import time
from collections.abc import Callable
from typing import Any


class TransientAPIError(Exception):
    pass


def with_retry(
    fn: Callable[[], Any],
    max_attempts: int = 4,
    base_delay_seconds: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[int], float] = lambda attempt: 0.0,
) -> Any:
    """Retry `fn` on TransientAPIError with exponential backoff.

    `sleep` and `jitter` are injectable so unit tests can fast-forward time
    deterministically. Non-transient exceptions propagate immediately.
    """
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except TransientAPIError as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            delay = base_delay_seconds * (2 ** (attempt - 1)) + jitter(attempt)
            sleep(delay)
    raise last_error


def classify_status(status_code: int) -> bool:
    """True if the HTTP status should be retried (transient)."""
    return status_code >= 500 or status_code == 429
