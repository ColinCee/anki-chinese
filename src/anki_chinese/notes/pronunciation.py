"""Pronunciation normalization helpers shared by notes and lookups."""

from __future__ import annotations

from collections.abc import Callable

from pypinyin.contrib.tone_convert import to_normal

from .model import CharacterNote


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


def reading_from_example(note: CharacterNote) -> str:
    if not note.example_word or not note.example_pinyin:
        return ""

    syllables = note.example_pinyin.split()
    if len(syllables) != len(note.example_word):
        return ""

    target_syllables = [
        syllables[index]
        for index, char in enumerate(note.example_word)
        if char == note.hanzi
    ]
    if not target_syllables:
        return ""

    normalized = [_normalize_syllable(syllable) for syllable in target_syllables]
    unique = list(dict.fromkeys(normalized))
    if len(unique) == 1:
        return target_syllables[0]
    return ""


def normalize_example_pinyin(
    note: CharacterNote,
    lookup_pinyin_word: Callable[[str], str],
) -> None:
    if not note.example_word or not note.example_pinyin:
        fallback = lookup_pinyin_word(note.example_word) if note.example_word else ""
        if fallback and len(fallback.split()) == len(note.example_word):
            note.example_pinyin = fallback
        return

    fallback = lookup_pinyin_word(note.example_word)
    if not fallback or len(fallback.split()) != len(note.example_word):
        return

    if len(note.example_pinyin.split()) != len(note.example_word):
        note.example_pinyin = fallback
        return

    current = [_normalize_syllable(syllable) for syllable in note.example_pinyin.split()]
    inferred = [_normalize_syllable(syllable) for syllable in fallback.split()]
    if current != inferred:
        note.example_pinyin = fallback
