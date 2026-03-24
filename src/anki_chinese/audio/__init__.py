"""Audio generation, provider boundaries, and file/tag helpers."""

from .azure import (
    AzureTTSProvider,
    TTSRateLimitError,
    TTSError,
    _generate_audio,
    _ssml_cantonese,
    _ssml_mandarin,
    _ssml_mandarin_text,
    _ssml_plain,
    _to_sapi_jyutping,
    _to_sapi_pinyin,
    generate_cantonese,
    generate_example_audio,
    generate_mandarin,
)
from .files import (
    audio_tasks_for_note,
    example_audio_filename,
    expected_cantonese_audio_tag,
    expected_example_audio_tag,
    expected_mandarin_audio_tag,
    is_valid_audio_tag,
)
from .provider import ProviderCapabilities, TTSProvider

__all__ = [
    "AzureTTSProvider",
    "ProviderCapabilities",
    "TTSProvider",
    "TTSRateLimitError",
    "TTSError",
    "_generate_audio",
    "_ssml_cantonese",
    "_ssml_mandarin",
    "_ssml_mandarin_text",
    "_ssml_plain",
    "_to_sapi_jyutping",
    "_to_sapi_pinyin",
    "audio_tasks_for_note",
    "example_audio_filename",
    "expected_cantonese_audio_tag",
    "expected_example_audio_tag",
    "expected_mandarin_audio_tag",
    "generate_cantonese",
    "generate_example_audio",
    "generate_mandarin",
    "is_valid_audio_tag",
]
