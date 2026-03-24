"""Retry policy configuration for rate-limited audio providers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    request_interval: float = 4.0
    rate_limit_retry_delay: float = 30.0
    max_attempts: int = 5


DEFAULT_RETRY_POLICY = RetryPolicy()
