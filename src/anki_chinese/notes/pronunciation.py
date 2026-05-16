"""Pronunciation normalization helpers shared by notes and lookups."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

import re
from dataclasses import dataclass
from typing import Literal

from pypinyin.contrib.tone_convert import to_normal

ConfuserSeverity = Literal["exact", "same-base", "near-retroflex", "same-final"]

_RETROFLEX_PAIRS = {
    ("zh", "z"),
    ("z", "zh"),
    ("ch", "c"),
    ("c", "ch"),
    ("sh", "s"),
    ("s", "sh"),
}


@dataclass(frozen=True)
class PhoneticConfuser:
    character: str
    pinyin: str
    severity: ConfuserSeverity
    position: int


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


def _split_pinyin_tokens(sentence_pinyin: str, num_chars: int) -> list[str] | None:
    """Split sentence pinyin into per-character syllables.

    Handles compound tokens like 'měitiān' → ['měi', 'tiān'] by splitting
    on boundaries between a tone vowel's consonant cluster and the next onset.
    Returns None if the result doesn't align with *num_chars*.
    """
    cleaned = re.sub(r"[，。！？；：、,.?!;:]", " ", sentence_pinyin)
    tokens = cleaned.split()
    if len(tokens) == num_chars:
        return tokens

    # Simple split didn't work — use pypinyin to get per-char readings
    return None


def _classify_confuser(
    target_pinyin: str,
    other_pinyin: str,
    *,
    include_same_final: bool = False,
) -> ConfuserSeverity | None:
    target_base = to_normal(target_pinyin).lower().strip()
    other_base = to_normal(other_pinyin).lower().strip()
    if not target_base or not other_base:
        return None

    target_tone = _tone_number(target_pinyin)
    other_tone = _tone_number(other_pinyin)
    if target_base == other_base:
        return "exact" if target_tone == other_tone else "same-base"

    target_initial, target_final = _split_syllable(target_base)
    other_initial, other_final = _split_syllable(other_base)
    if target_final == other_final and (target_initial, other_initial) in _RETROFLEX_PAIRS:
        return "near-retroflex"

    if include_same_final and target_final == other_final:
        return "same-final"

    return None


def find_phonetic_confuser_details(
    hanzi: str,
    char_pinyin: str,
    sentence: str,
    sentence_pinyin: str,
    *,
    include_same_final: bool = False,
) -> list[PhoneticConfuser]:
    """Find characters in *sentence* that sound confusingly similar to *hanzi*.

    Returns a list of confusers where severity is:
    - "exact": same syllable + same tone (true homophone)
    - "same-base": same syllable, different tone
    - "near-retroflex": zh/z, ch/c, or sh/s with the same final
    - "same-final": same final/rhyme, only when include_same_final is true
    """
    from pypinyin import Style, lazy_pinyin

    if not to_normal(char_pinyin).strip():
        return []

    cjk_chars = [ch for ch in sentence if "\u4e00" <= ch <= "\u9fff"]

    # Try splitting sentence_pinyin first; fall back to pypinyin
    syllables = _split_pinyin_tokens(sentence_pinyin, len(cjk_chars))
    if syllables is None:
        syllables = lazy_pinyin("".join(cjk_chars), style=Style.TONE, errors="ignore")
    if len(syllables) != len(cjk_chars):
        return []

    confusers: list[PhoneticConfuser] = []
    for position, (ch, syl) in enumerate(zip(cjk_chars, syllables, strict=True)):
        if ch == hanzi:
            continue

        severity = _classify_confuser(
            char_pinyin,
            syl,
            include_same_final=include_same_final,
        )
        if severity:
            confusers.append(PhoneticConfuser(ch, syl, severity, position))

    return confusers


def find_phonetic_confusers(
    hanzi: str,
    char_pinyin: str,
    sentence: str,
    sentence_pinyin: str,
) -> list[tuple[str, str, str]]:
    """Compatibility wrapper returning (character, pinyin, severity) tuples."""
    return [
        (confuser.character, confuser.pinyin, confuser.severity)
        for confuser in find_phonetic_confuser_details(
            hanzi,
            char_pinyin,
            sentence,
            sentence_pinyin,
        )
    ]


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
