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

from pathlib import Path

from .. import config
from ..notes.pronunciation import normalize_pinyin, reading_matches
from .cache import MemoizedLoader
from ._jyutping import lookup_jyutping, lookup_jyutping_word
from ._overrides import load_example_overrides
from ._pinyin import lookup_pinyin, lookup_pinyin_word

def _pick_example(
    candidates: list[tuple[str, str, str]],
    *,
    hanzi: str,
    preferred_pinyin: str,
) -> tuple[str, str, str]:
    if not candidates:
        return "", "", ""

    for word, meaning, pinyin in candidates:
        if reading_matches(hanzi, word, pinyin, preferred_pinyin):
            return word, meaning, pinyin

    return candidates[0]


class LookupService:
    """Owns cached indexes and lookup paths for example selection."""

    def __init__(
        self,
        *,
        example_words_path: Path,
        hsk_vocab_path: Path,
        cedict_path: Path,
        subtlex_path: Path | None,
    ) -> None:
        self.example_words_path = example_words_path
        self.hsk_vocab_path = hsk_vocab_path
        self.cedict_path = cedict_path
        self.subtlex_path = subtlex_path
        self._hsk_indexes = MemoizedLoader[Path, dict[str, list[tuple[str, str, str]]]]()
        self._cedict_indexes = MemoizedLoader[
            tuple[Path, Path | None], dict[str, list[tuple[str, str, str]]]
        ]()

    def _get_hsk_index(self) -> dict[str, list[tuple[str, str, str]]]:
        from . import _hsk

        return self._hsk_indexes.get_or_load(
            self.hsk_vocab_path,
            lambda: _hsk.build_index(self.hsk_vocab_path),
        )

    def _get_cedict_index(self) -> dict[str, list[tuple[str, str, str]]]:
        from . import _cedict

        cache_key = (self.cedict_path, self.subtlex_path)
        return self._cedict_indexes.get_or_load(
            cache_key,
            lambda: _cedict.build_index(self.cedict_path, self.subtlex_path),
        )

    def lookup_example(
        self,
        hanzi: str,
        preferred_pinyin: str = "",
    ) -> tuple[str, str, str]:
        overrides = load_example_overrides(self.example_words_path)
        entry = overrides.get(hanzi, {})
        word = entry.get("word", "")
        if word:
            pinyin = entry.get("pinyin", "") or lookup_pinyin_word(word)
            return word, entry.get("meaning", ""), normalize_pinyin(pinyin)

        hsk_word, hsk_meaning, hsk_pinyin = _pick_example(
            self._get_hsk_index().get(hanzi, []),
            hanzi=hanzi,
            preferred_pinyin=preferred_pinyin,
        )
        if hsk_word:
            return hsk_word, hsk_meaning, hsk_pinyin

        cedict_word, cedict_meaning, cedict_pinyin = _pick_example(
            self._get_cedict_index().get(hanzi, []),
            hanzi=hanzi,
            preferred_pinyin=preferred_pinyin,
        )
        if cedict_word:
            return cedict_word, cedict_meaning, cedict_pinyin

        return "", "", ""


DEFAULT_LOOKUP_SERVICE = LookupService(
    example_words_path=config.EXAMPLE_WORDS_PATH,
    hsk_vocab_path=config.HSK_VOCAB_PATH,
    cedict_path=config.CEDICT_PATH,
    subtlex_path=config.SUBTLEX_PATH,
)


def lookup_example(hanzi: str, preferred_pinyin: str = "") -> tuple[str, str, str]:
    """Return (example_word, example_meaning, example_pinyin) for *hanzi*."""
    return DEFAULT_LOOKUP_SERVICE.lookup_example(hanzi, preferred_pinyin)


__all__ = [
    "DEFAULT_LOOKUP_SERVICE",
    "LookupService",
    "lookup_example",
    "lookup_jyutping",
    "lookup_jyutping_word",
    "lookup_pinyin",
    "lookup_pinyin_word",
]
