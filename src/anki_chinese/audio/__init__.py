"""Audio generation, provider boundaries, and file/tag helpers."""

from .errors import TTSConfigurationError, TTSError, TTSRateLimitError, classify_http_error
from .factory import PROVIDER_NAMES, build_tts_provider
from .files import (
    audio_tasks_for_note,
    example_audio_filename,
    expected_cantonese_audio_tag,
    expected_example_audio_tag,
    expected_mandarin_audio_tag,
    expected_sentence_audio_tag,
    is_valid_audio_tag,
    preview_mandarin_filename,
)
from .provider import ProviderCapabilities, TTSProvider
from .rate_limit import NoOpRateLimiter, RateLimiter, SlidingWindowRateLimiter
from .retry import synthesize_with_retry

__all__ = [
    "NoOpRateLimiter",
    "PROVIDER_NAMES",
    "ProviderCapabilities",
    "RateLimiter",
    "SlidingWindowRateLimiter",
    "TTSProvider",
    "TTSConfigurationError",
    "TTSRateLimitError",
    "TTSError",
    "classify_http_error",
    "synthesize_with_retry",
    "audio_tasks_for_note",
    "build_tts_provider",
    "example_audio_filename",
    "expected_cantonese_audio_tag",
    "expected_example_audio_tag",
    "expected_mandarin_audio_tag",
    "expected_sentence_audio_tag",
    "is_valid_audio_tag",
    "preview_mandarin_filename",
]
