"""Rate limiter abstractions for outbound TTS requests."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from threading import Lock
from typing import Protocol


class RateLimiter(Protocol):
    def acquire(self) -> None: ...


class NoOpRateLimiter:
    def acquire(self) -> None:
        return


class SlidingWindowRateLimiter:
    """Allow up to N request starts inside a moving time window."""

    def __init__(
        self,
        *,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clock = clock
        self._sleep = sleep
        self._lock = Lock()
        self._timestamps: deque[float] = deque()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                self._prune_expired(now)
                if len(self._timestamps) < self.max_requests:
                    self._timestamps.append(now)
                    return

                wait_seconds = self.window_seconds - (now - self._timestamps[0])

            if wait_seconds > 0:
                self._sleep(wait_seconds)

    def _prune_expired(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()
