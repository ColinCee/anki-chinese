"""Pronunciation normalization helpers shared by notes and lookups."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

from pypinyin.contrib.tone_convert import to_normal


def normalize_pinyin(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _normalize_syllable(syllable: str) -> str:
    return to_normal(syllable).lower().replace("u:", "v")


def reading_matches(
    hanzi: str,
    word: str,
    word_pinyin: str,
    preferred_pinyin: str,
) -> bool:
    preferred = normalize_pinyin(preferred_pinyin)
    if not preferred or hanzi not in word:
        return True

    syllables = word_pinyin.split()
    if len(syllables) != len(word):
        return False

    return any(
        syllables[index] == preferred for index, char in enumerate(word) if char == hanzi
    )
