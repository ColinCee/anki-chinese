"""Audio generation, provider boundaries, and file/tag helpers."""

from .errors import TTSConfigurationError, TTSRateLimitError, TTSError
from .factory import build_tts_provider
from .files import (
    audio_tasks_for_note,
    example_audio_filename,
    expected_cantonese_audio_tag,
    expected_example_audio_tag,
    expected_mandarin_audio_tag,
    is_valid_audio_tag,
    preview_mandarin_filename,
)
from .provider import ProviderCapabilities, TTSProvider

__all__ = [
    "ProviderCapabilities",
    "TTSProvider",
    "TTSConfigurationError",
    "TTSRateLimitError",
    "TTSError",
    "audio_tasks_for_note",
    "build_tts_provider",
    "example_audio_filename",
    "expected_cantonese_audio_tag",
    "expected_example_audio_tag",
    "expected_mandarin_audio_tag",
    "is_valid_audio_tag",
    "preview_mandarin_filename",
]
