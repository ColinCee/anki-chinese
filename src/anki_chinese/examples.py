"""
Example word lookup.

Uses a bundled subset of CC-CEDICT filtered to common/HSK words.
This module provides a simple lookup: given a character, return the most
common 2-character word containing it, plus its English meaning.

The actual word list is loaded from data/example_words.json which you can
edit freely.  Format:

    {
        "早": {"word": "早安", "meaning": "good morning"},
        "行": {"word": "银行", "meaning": "bank"},
        ...
    }

If a character has no entry, the example fields are left empty.
A future CLI command can auto-populate this file from CC-CEDICT / HSK lists.
"""

from __future__ import annotations

import json
from typing import Iterable

try:
    import jieba  # type: ignore[import-not-found]
except ImportError:
    jieba = None  # type: ignore[assignment]

from .config import DATA_DIR

EXAMPLE_WORDS_PATH = DATA_DIR / "example_words.json"

_cache: dict[str, dict[str, str]] | None = None
_auto_best_word: dict[str, str] | None = None


def _is_cjk(word: str) -> bool:
    return all("\u4e00" <= ch <= "\u9fff" for ch in word)


def _iter_jieba_words() -> Iterable[tuple[str, int]]:
    if jieba is None:
        return []

    # jieba's core dictionary is word -> frequency.
    freq_map = getattr(jieba.dt, "FREQ", None)
    if not isinstance(freq_map, dict):
        return []

    items: list[tuple[str, int]] = []
    for word, freq in freq_map.items():
        if not isinstance(word, str) or not isinstance(freq, int):
            continue
        if len(word) != 2:
            continue
        if not _is_cjk(word):
            continue
        items.append((word, freq))
    return items


def _build_auto_index() -> dict[str, str]:
    """Build best 2-character example word per hanzi using jieba frequencies."""
    best: dict[str, tuple[str, int]] = {}

    for word, freq in _iter_jieba_words():
        for ch in set(word):
            prev = best.get(ch)
            if prev is None or freq > prev[1]:
                best[ch] = (word, freq)

    return {ch: word for ch, (word, _) in best.items()}


def _lookup_auto(hanzi: str) -> str:
    global _auto_best_word
    if _auto_best_word is None:
        _auto_best_word = _build_auto_index()
    return _auto_best_word.get(hanzi, "")


def _load() -> dict[str, dict[str, str]]:
    global _cache
    if _cache is not None:
        return _cache
    if EXAMPLE_WORDS_PATH.exists():
        with open(EXAMPLE_WORDS_PATH, encoding="utf-8") as f:
            data: dict[str, dict[str, str]] = json.load(f)
            _cache = data
    else:
        _cache = {}
    return _cache


def lookup_example(hanzi: str) -> tuple[str, str]:
    """Return (example_word, example_meaning) for a character, or ("", "")."""
    data = _load()
    entry = data.get(hanzi, {})

    # Manual examples always win.
    word = entry.get("word", "")
    if word:
        return word, entry.get("meaning", "")

    # Auto fallback (common 2-char word by frequency).
    auto_word = _lookup_auto(hanzi)
    if auto_word:
        return auto_word, ""

    return "", ""


def save_examples(examples: dict[str, dict]) -> None:
    """Write the example words file."""
    EXAMPLE_WORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EXAMPLE_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(examples, f, ensure_ascii=False, indent=2)
