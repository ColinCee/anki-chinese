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

from .config import DATA_DIR

EXAMPLE_WORDS_PATH = DATA_DIR / "example_words.json"

_cache: dict[str, dict[str, str]] | None = None


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
    return entry.get("word", ""), entry.get("meaning", "")


def save_examples(examples: dict[str, dict]) -> None:
    """Write the example words file."""
    EXAMPLE_WORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EXAMPLE_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(examples, f, ensure_ascii=False, indent=2)
