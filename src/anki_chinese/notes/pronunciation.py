"""Pronunciation normalization helpers shared by notes and lookups."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

import re
from dataclasses import dataclass
from typing import Literal

from pypinyin.contrib.tone_convert import to_normal

ConfuserSeverity = Literal["exact", "same-base", "near-retroflex", "same-final"]

_PINYIN_SYLLABLES: set[str] | None = None

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


@dataclass(frozen=True)
class SentencePinyinIssue:
    expected_pinyin: str
    stored_pinyin: str
    reason: str


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


def _compact_pinyin(text: str) -> str:
    normalized = to_normal(text.lower().replace("u:", "v"))
    return re.sub(r"[\s，。！？；：、,.?!;:·'’`-]+", "", normalized)


def _pinyin_syllables() -> set[str]:
    global _PINYIN_SYLLABLES
    if _PINYIN_SYLLABLES is None:
        from pypinyin.constants import PINYIN_DICT

        syllables = set()
        for readings in PINYIN_DICT.values():
            for reading in readings.split(","):
                syllables.add(to_normal(reading).lower().replace("u:", "v"))
        _PINYIN_SYLLABLES = syllables
    return _PINYIN_SYLLABLES


def _split_compound_pinyin_token(token: str) -> list[str] | None:
    normalized = _compact_pinyin(token).replace("ü", "v")
    if not normalized:
        return []

    if normalized.endswith("r") and normalized != "er":
        stem = normalized[:-1]
        stem_syllables = _split_compound_pinyin_token(stem)
        if stem_syllables:
            return [*stem_syllables, "er"]

    syllables = _pinyin_syllables()
    best: list[str] | None = None

    def search(index: int, parts: list[str]) -> None:
        nonlocal best
        if best is not None and len(parts) >= len(best):
            return
        if index == len(normalized):
            best = parts.copy()
            return
        for end in range(len(normalized), index, -1):
            piece = normalized[index:end]
            if piece in syllables:
                search(end, [*parts, piece])

    search(0, [])
    return best


def _split_stored_sentence_pinyin(sentence_pinyin: str) -> list[str] | None:
    tokens = [
        token
        for token in re.split(r"[\s，。！？；：、,.?!;:·'’`-]+", sentence_pinyin)
        if token
    ]
    syllables: list[str] = []
    for token in tokens:
        token_syllables = _split_compound_pinyin_token(token)
        if token_syllables is None:
            return None
        syllables.extend(token_syllables)
    return syllables


def _cjk_chars(text: str) -> list[str]:
    return [ch for ch in text if "\u4e00" <= ch <= "\u9fff"]


def _allowed_pinyin_bases(char: str) -> set[str]:
    from pypinyin import Style, pinyin

    readings = pinyin(char, style=Style.NORMAL, heteronym=True, errors="ignore")
    if not readings:
        return set()
    return {reading.lower().replace("u:", "v") for reading in readings[0]}


def expected_sentence_pinyin(sentence: str) -> str:
    """Return pypinyin's per-character reading for CJK text in *sentence*."""
    from pypinyin import Style, lazy_pinyin

    cjk_text = "".join(_cjk_chars(sentence))
    if not cjk_text:
        return ""
    return " ".join(lazy_pinyin(cjk_text, style=Style.TONE, errors="ignore"))


def audit_sentence_pinyin(sentence: str, sentence_pinyin: str) -> SentencePinyinIssue | None:
    """Flag stored sentence pinyin readings that do not fit the sentence text."""
    expected = expected_sentence_pinyin(sentence)
    cjk_chars = _cjk_chars(sentence)
    if not expected:
        return None
    stored = sentence_pinyin.strip()
    if not stored:
        return SentencePinyinIssue(
            expected_pinyin=expected,
            stored_pinyin=sentence_pinyin,
            reason="missing pinyin",
        )
    if _compact_pinyin(stored) == _compact_pinyin(expected):
        return None
    stored_syllables = _split_stored_sentence_pinyin(stored)
    if stored_syllables is None:
        return SentencePinyinIssue(
            expected_pinyin=expected,
            stored_pinyin=sentence_pinyin,
            reason="unparseable pinyin",
        )
    if len(stored_syllables) != len(cjk_chars):
        return SentencePinyinIssue(
            expected_pinyin=expected,
            stored_pinyin=sentence_pinyin,
            reason="syllable count mismatch",
        )
    for char, syllable in zip(cjk_chars, stored_syllables, strict=True):
        allowed = _allowed_pinyin_bases(char)
        if allowed and syllable not in allowed:
            return SentencePinyinIssue(
                expected_pinyin=expected,
                stored_pinyin=sentence_pinyin,
                reason=f"reading mismatch at {char}",
            )
    return None


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
