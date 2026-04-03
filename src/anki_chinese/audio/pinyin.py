"""Pinyin tone-mark conversion: diacritical ↔ numbered."""

from __future__ import annotations

# Maps each toned vowel to (base_vowel, tone_number).
_TONED_TO_BASE: dict[str, tuple[str, str]] = {
    "ā": ("a", "1"),
    "á": ("a", "2"),
    "ǎ": ("a", "3"),
    "à": ("a", "4"),
    "ē": ("e", "1"),
    "é": ("e", "2"),
    "ě": ("e", "3"),
    "è": ("e", "4"),
    "ī": ("i", "1"),
    "í": ("i", "2"),
    "ǐ": ("i", "3"),
    "ì": ("i", "4"),
    "ō": ("o", "1"),
    "ó": ("o", "2"),
    "ǒ": ("o", "3"),
    "ò": ("o", "4"),
    "ū": ("u", "1"),
    "ú": ("u", "2"),
    "ǔ": ("u", "3"),
    "ù": ("u", "4"),
    "ǖ": ("ü", "1"),
    "ǘ": ("ü", "2"),
    "ǚ": ("ü", "3"),
    "ǜ": ("ü", "4"),
}


def diacritical_to_numbered(pinyin: str) -> str:
    """Convert diacritical pinyin to numbered pinyin.

    Examples:
        "nǐ" → "ni3"
        "nǐ hǎo" → "ni3 hao3"
        "yī" → "yi1"
        "ma" → "ma5"  (neutral tone)
    """
    return " ".join(_convert_syllable(s) for s in pinyin.split())


def _convert_syllable(syllable: str) -> str:
    tone = "5"  # neutral tone if no mark found
    result: list[str] = []
    for ch in syllable:
        if ch in _TONED_TO_BASE:
            base, tone = _TONED_TO_BASE[ch]
            result.append(base)
        else:
            result.append(ch)
    return "".join(result) + tone
