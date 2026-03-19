"""
Public API for all data-source lookups.

Callers import from here — never from the private _*.py modules directly.

Lookup chain for example words:
    1. Manual overrides  (data/example_words.json)
    2. HSK 3.0 vocab     (data/hsk_complete.min.json  — auto-downloaded)
    3. CC-CEDICT         (data/cedict_1_0_ts_utf-8_mdbg.txt — auto-downloaded)
       scored by SUBTLEX-CH frequency when data/SUBTLEX_CH.xlsx is present
"""

from __future__ import annotations

from .. import config
from ._jyutping import lookup_jyutping, lookup_jyutping_word
from ._overrides import load_example_overrides
from ._pinyin import lookup_pinyin, lookup_pinyin_word

# Module-level lazy indexes — built once on first use
_hsk_index: dict[str, list[tuple[str, str, str]]] | None = None
_cedict_index: dict[str, list[tuple[str, str, str]]] | None = None


def _get_hsk_index() -> dict[str, list[tuple[str, str, str]]]:
    global _hsk_index
    if _hsk_index is None:
        from . import _hsk

        _hsk_index = _hsk.build_index(config.HSK_VOCAB_PATH)
    return _hsk_index


def _get_cedict_index() -> dict[str, list[tuple[str, str, str]]]:
    global _cedict_index
    if _cedict_index is None:
        from . import _cedict

        _cedict_index = _cedict.build_index(config.CEDICT_PATH, config.SUBTLEX_PATH)
    return _cedict_index


def _normalize_pinyin(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _reading_matches(
    hanzi: str,
    word: str,
    word_pinyin: str,
    preferred_pinyin: str,
) -> bool:
    preferred = _normalize_pinyin(preferred_pinyin)
    if not preferred or hanzi not in word:
        return True

    syllables = word_pinyin.split()
    if len(syllables) != len(word):
        return False

    return any(
        syllables[index] == preferred for index, ch in enumerate(word) if ch == hanzi
    )


def _pick_example(
    candidates: list[tuple[str, str, str]],
    *,
    hanzi: str,
    preferred_pinyin: str,
) -> tuple[str, str, str]:
    if not candidates:
        return "", "", ""

    for word, meaning, pinyin in candidates:
        if _reading_matches(hanzi, word, pinyin, preferred_pinyin):
            return word, meaning, pinyin

    return candidates[0]


def lookup_example(hanzi: str, preferred_pinyin: str = "") -> tuple[str, str, str]:
    """Return (example_word, example_meaning, example_pinyin) for *hanzi*.

    Consults sources in priority order:
        1. Manual overrides (example_words.json) — always wins
        2. HSK 3.0 vocabulary — best 2-char word by frequency rank
        3. CC-CEDICT + optional SUBTLEX-CH scoring
    """
    # 1. Manual overrides
    overrides = load_example_overrides(config.EXAMPLE_WORDS_PATH)
    entry = overrides.get(hanzi, {})
    word = entry.get("word", "")
    if word:
        pinyin = entry.get("pinyin", "") or lookup_pinyin_word(word)
        return word, entry.get("meaning", ""), _normalize_pinyin(pinyin)

    # 2. HSK
    hsk_word, hsk_meaning, hsk_pinyin = _pick_example(
        _get_hsk_index().get(hanzi, []),
        hanzi=hanzi,
        preferred_pinyin=preferred_pinyin,
    )
    if hsk_word:
        return hsk_word, hsk_meaning, hsk_pinyin

    # 3. CC-CEDICT (with optional SUBTLEX scoring)
    cedict_word, cedict_meaning, cedict_pinyin = _pick_example(
        _get_cedict_index().get(hanzi, []),
        hanzi=hanzi,
        preferred_pinyin=preferred_pinyin,
    )
    if cedict_word:
        return cedict_word, cedict_meaning, cedict_pinyin

    return "", "", ""


__all__ = [
    "lookup_example",
    "lookup_jyutping",
    "lookup_jyutping_word",
    "lookup_pinyin",
    "lookup_pinyin_word",
]
