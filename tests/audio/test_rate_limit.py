import pytest

from anki_chinese.audio.rate_limit import NoOpRateLimiter, SlidingWindowRateLimiter


def test_noop_rate_limiter_never_blocks() -> None:
    limiter = NoOpRateLimiter()

    limiter.acquire()
    limiter.acquire()


def test_sliding_window_rate_limiter_allows_requests_within_capacity() -> None:
    current_time = 0.0
    sleep_calls: list[float] = []

    def clock() -> float:
        return current_time

    def sleep(seconds: float) -> None:
        nonlocal current_time
        sleep_calls.append(seconds)
        current_time += seconds

    limiter = SlidingWindowRateLimiter(
        max_requests=2,
        window_seconds=10.0,
        clock=clock,
        sleep=sleep,
    )

    limiter.acquire()
    current_time = 1.0
    limiter.acquire()

    assert sleep_calls == []


def test_sliding_window_rate_limiter_waits_until_oldest_request_expires() -> None:
    current_time = 0.0
    sleep_calls: list[float] = []

    def clock() -> float:
        return current_time

    def sleep(seconds: float) -> None:
        nonlocal current_time
        sleep_calls.append(seconds)
        current_time += seconds

    limiter = SlidingWindowRateLimiter(
        max_requests=2,
        window_seconds=10.0,
        clock=clock,
        sleep=sleep,
    )

    limiter.acquire()  # t=0
    current_time = 1.0
    limiter.acquire()  # t=1
    current_time = 2.0
    limiter.acquire()  # waits until t=10, then proceeds

    assert sleep_calls == [8.0]


def test_sliding_window_rate_limiter_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_requests=0, window_seconds=60.0)

    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_requests=60, window_seconds=0.0)
