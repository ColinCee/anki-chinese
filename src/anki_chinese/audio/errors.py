"""Provider-neutral TTS error types."""

from __future__ import annotations


class TTSError(RuntimeError):
    """Base error for speech synthesis failures."""


class TTSConfigurationError(TTSError):
    """Speech synthesis cannot proceed because local configuration is invalid."""


class TTSRateLimitError(TTSError):
    """Speech synthesis failed because the provider rate limited the request."""


def is_rate_limited_message(message: str) -> bool:
    lowered = message.lower()
    return (
        "429" in lowered
        or "rate limit" in lowered
        or "rate limited" in lowered
        or "too many requests" in lowered
    )
