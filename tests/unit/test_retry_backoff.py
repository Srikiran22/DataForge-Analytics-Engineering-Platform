import pytest

from ingestion.extractors.retry import TransientAPIError, classify_status, with_retry


class FakeClock:
    def __init__(self):
        self.sleeps = []

    def sleep(self, seconds: float):
        self.sleeps.append(seconds)


def test_retries_then_succeeds_with_exponential_backoff():
    clock = FakeClock()
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TransientAPIError("boom")
        return "ok"

    result = with_retry(flaky, max_attempts=4, base_delay_seconds=0.5, sleep=clock.sleep)

    assert result == "ok"
    assert attempts["n"] == 3
    assert clock.sleeps == [0.5, 1.0]


def test_gives_up_after_max_attempts_and_raises_last_error():
    clock = FakeClock()

    def always_fails():
        raise TransientAPIError("down")

    with pytest.raises(TransientAPIError, match="down"):
        with_retry(always_fails, max_attempts=3, base_delay_seconds=0.25, sleep=clock.sleep)

    assert clock.sleeps == [0.25, 0.5]


def test_does_not_retry_non_transient_errors():
    class Fatal(Exception):
        pass

    calls = {"n": 0}

    def fatal():
        calls["n"] += 1
        raise Fatal("bad request")

    with pytest.raises(Fatal):
        with_retry(fatal, max_attempts=4, sleep=lambda s: None)

    assert calls["n"] == 1


def test_status_classification():
    assert classify_status(500)
    assert classify_status(503)
    assert classify_status(429)
    assert not classify_status(404)
    assert not classify_status(200)
