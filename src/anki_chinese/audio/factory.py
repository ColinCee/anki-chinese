"""TTS provider construction."""

from __future__ import annotations

from pathlib import Path

from ..config import GENERATED_AUDIO_DIR
from .minimax import MiniMaxTTSProvider
from .provider import TTSProvider

def build_tts_provider(*, generated_audio_dir: Path = GENERATED_AUDIO_DIR) -> TTSProvider:
    return MiniMaxTTSProvider(generated_audio_dir=generated_audio_dir)
