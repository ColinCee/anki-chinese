"""Pronunciation normalization helpers shared by notes and lookups."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

from pypinyin.contrib.tone_convert import to_normal

# Pinyin initials sorted longest-first for greedy matching
_INITIALS = (
    "zh",
    "ch",
    "sh",
    "b",
    "p",
    "m",
    "f",
    "d",
    "t",
    "n",
    "l",
    "g",
    "k",
    "h",
    "j",
    "q",
    "x",
    "z",
    "c",
    "s",
    "r",
    "y",
    "w",
)


def normalize_pinyin(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _normalize_syllable(syllable: str) -> str:
    return to_normal(syllable).lower().replace("u:", "v")


def _split_syllable(pinyin: str) -> tuple[str, str]:
    """Split a pinyin syllable into (initial, final)."""
    base = to_normal(pinyin).lower().strip()
    for ini in _INITIALS:
        if base.startswith(ini):
            return ini, base[len(ini) :]
    return "", base


def _tone_number(pinyin: str) -> int:
    """Extract tone number (1-4) from diacritical pinyin; 5 = neutral."""
    tone_map = {
        "ā": 1,
        "á": 2,
        "ǎ": 3,
        "à": 4,
        "ē": 1,
        "é": 2,
        "ě": 3,
        "è": 4,
        "ī": 1,
        "í": 2,
        "ǐ": 3,
        "ì": 4,
        "ō": 1,
        "ó": 2,
        "ǒ": 3,
        "ò": 4,
        "ū": 1,
        "ú": 2,
        "ǔ": 3,
        "ù": 4,
        "ǖ": 1,
        "ǘ": 2,
        "ǚ": 3,
        "ǜ": 4,
    }
    for ch in pinyin:
        if ch in tone_map:
            return tone_map[ch]
    return 5


def find_phonetic_confusers(
    hanzi: str,
    char_pinyin: str,
    sentence: str,
    sentence_pinyin: str,
) -> list[tuple[str, str, str]]:
    """Find characters in *sentence* that sound confusingly similar to *hanzi*.

    Returns list of (character, its_pinyin, severity) where severity is:
    - "exact": same syllable + same tone (true homophone)
    - "same-base": same syllable, different tone
    """
    char_base = to_normal(char_pinyin).lower().strip()
    char_tone = _tone_number(char_pinyin)

    if not char_base:
        return []

    cjk_chars = [(i, ch) for i, ch in enumerate(sentence) if "\u4e00" <= ch <= "\u9fff"]
    syllables = sentence_pinyin.split()

    if len(cjk_chars) != len(syllables):
        return []

    confusers: list[tuple[str, str, str]] = []
    for (_, ch), syl in zip(cjk_chars, syllables, strict=True):
        if ch == hanzi:
            continue

        s_base = to_normal(syl).lower().strip()
        s_tone = _tone_number(syl)

        if s_base == char_base:
            severity = "exact" if s_tone == char_tone else "same-base"
            confusers.append((ch, syl, severity))

    return confusers


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

    return any(syllables[index] == preferred for index, char in enumerate(word) if char == hanzi)
