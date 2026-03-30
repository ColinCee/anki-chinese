"""Provider-neutral TTS error types."""

from __future__ import annotations

import json
from urllib.error import HTTPError


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


def classify_http_error(
    error: HTTPError,
    *,
    provider_name: str,
    extract_message: str = "",
    config_hint: str = "",
) -> TTSError:
    """Turn an HTTPError into the appropriate TTSError subclass.

    ``extract_message`` is a pre-parsed message from the response body.
    If empty, the raw body is read and parsed as JSON with a ``error.message``
    fallback.  ``config_hint`` is appended to configuration errors.
    """
    if not extract_message:
        body = error.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
            extract_message = (
                data.get("error", {}).get("message", "")
                or body.strip()
                or f"{provider_name} request failed with HTTP {error.code}"
            )
        except json.JSONDecodeError:
            extract_message = (
                body.strip()
                or f"{provider_name} request failed with HTTP {error.code}"
            )

    if error.code in {401, 403} or "invalid api key" in extract_message.lower():
        hint = f" {config_hint}" if config_hint else ""
        return TTSConfigurationError(f"{extract_message}{hint}")
    if error.code == 429 or is_rate_limited_message(extract_message):
        return TTSRateLimitError(extract_message)
    return TTSError(extract_message)
