"""Retry policy and shared synthesis retry loop."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .errors import TTSError, TTSRateLimitError
from .files import is_valid_audio_file
from .rate_limit import RateLimiter


@dataclass(frozen=True)
class RetryPolicy:
    rate_limit_retry_delay: float = 30.0
    max_attempts: int = 5


DEFAULT_RETRY_POLICY = RetryPolicy()


def synthesize_with_retry(
    *,
    synthesize: Callable[[], bytes],
    output_path: Path,
    retry_policy: RetryPolicy,
    rate_limiter: RateLimiter,
    provider_name: str,
    cleanup: Callable[[], None] | None = None,
) -> None:
    """Run a synthesis function with rate-limit retry and file validation.

    ``synthesize`` must return raw audio bytes or raise a TTS error.
    ``cleanup`` is called before each attempt and on any error (e.g. to
    remove partial files).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, retry_policy.max_attempts + 1):
        if attempt > 1:
            time.sleep(retry_policy.rate_limit_retry_delay)

        if cleanup:
            cleanup()
        rate_limiter.acquire()

        try:
            audio_bytes = synthesize()
        except TTSRateLimitError:
            if cleanup:
                cleanup()
            if attempt < retry_policy.max_attempts:
                continue
            raise TTSRateLimitError(
                f"{provider_name} rate limited after {attempt} attempts"
            ) from None
        except TTSError:
            if cleanup:
                cleanup()
            raise

        output_path.write_bytes(audio_bytes)
        if is_valid_audio_file(output_path):
            return

        if cleanup:
            cleanup()
        raise TTSError(f"TTS did not create audio for {output_path.name}")

    raise TTSRateLimitError(
        f"{provider_name} rate limited after {retry_policy.max_attempts} attempts"
    )
