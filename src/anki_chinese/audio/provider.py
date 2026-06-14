"""Provider-facing audio abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderCapabilities:
    name: str
    supports_mandarin: bool
    supports_cantonese: bool
    supports_phoneme_control: bool


@dataclass(frozen=True)
class AudioGenerationProfile:
    provider: str
    model: str
    voice: str
    language_code: str
    settings: dict[str, str | int | float | bool]


class TTSProvider(Protocol):
    def capabilities(self) -> ProviderCapabilities: ...

    def generation_profile(self, kind: str) -> AudioGenerationProfile: ...

    def generate_mandarin(self, hanzi: str, pinyin: str, *, force: bool = False) -> str: ...

    def generate_plain_mandarin(self, text: str, *, force: bool = False) -> str: ...

    def generate_cantonese(self, hanzi: str, jyutping: str, *, force: bool = False) -> str: ...

    def generate_sentence_audio(self, hanzi: str, sentence: str, *, force: bool = False) -> str: ...

    def is_valid_audio_tag(self, tag: str) -> bool: ...
