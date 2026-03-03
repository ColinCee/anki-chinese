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
_hsk_index: dict[str, tuple[str, str]] | None = None
_cedict_index: dict[str, tuple[str, str]] | None = None


def _get_hsk_index() -> dict[str, tuple[str, str]]:
    global _hsk_index
    if _hsk_index is None:
        from . import _hsk

        _hsk_index = _hsk.build_index(config.HSK_VOCAB_PATH)
    return _hsk_index


def _get_cedict_index() -> dict[str, tuple[str, str]]:
    global _cedict_index
    if _cedict_index is None:
        from . import _cedict

        _cedict_index = _cedict.build_index(config.CEDICT_PATH, config.SUBTLEX_PATH)
    return _cedict_index


def lookup_example(hanzi: str) -> tuple[str, str]:
    """Return (example_word, example_meaning) for *hanzi*, or ("", "").

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
        return word, entry.get("meaning", "")

    # 2. HSK
    hsk_word, hsk_meaning = _get_hsk_index().get(hanzi, ("", ""))
    if hsk_word:
        return hsk_word, hsk_meaning

    # 3. CC-CEDICT (with optional SUBTLEX scoring)
    cedict_word, cedict_meaning = _get_cedict_index().get(hanzi, ("", ""))
    if cedict_word:
        return cedict_word, cedict_meaning

    return "", ""


__all__ = [
    "lookup_example",
    "lookup_jyutping",
    "lookup_jyutping_word",
    "lookup_pinyin",
    "lookup_pinyin_word",
]
