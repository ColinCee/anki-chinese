"""TTS provider construction."""

from __future__ import annotations

from pathlib import Path

from ..config import GENERATED_AUDIO_DIR
from .provider import TTSProvider

PROVIDER_NAMES = ("minimax", "google")
DEFAULT_PROVIDER = "google"


def build_tts_provider(
    *,
    generated_audio_dir: Path = GENERATED_AUDIO_DIR,
    provider_name: str | None = None,
) -> TTSProvider:
    """Build a TTS provider by name.

    Supported values: "google" (default), "minimax".
    """
    name = (provider_name or DEFAULT_PROVIDER).strip().lower()

    if name == "google":
        from .google_tts import GoogleTTSProvider

        return GoogleTTSProvider(generated_audio_dir=generated_audio_dir)

    from .minimax import MiniMaxTTSProvider

    return MiniMaxTTSProvider(generated_audio_dir=generated_audio_dir)
