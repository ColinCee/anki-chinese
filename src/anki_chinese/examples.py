"""
Example word lookup.

Uses Complete HSK Vocabulary (HSK 3.0 compatible) frequency data.
This module provides a lookup: given a character, return the most common
2-character word containing it, plus an English meaning when available.

The actual word list is loaded from data/example_words.json which you can
edit freely.  Format:

    {
        "早": {"word": "早安", "meaning": "good morning"},
        "行": {"word": "银行", "meaning": "bank"},
        ...
    }

If a character has no entry, the example fields are left empty.
"""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import urlopen

from .config import DATA_DIR

EXAMPLE_WORDS_PATH = DATA_DIR / "example_words.json"
HSK_VOCAB_PATH = DATA_DIR / "hsk_complete.min.json"
HSK_VOCAB_URL = (
    "https://raw.githubusercontent.com/drkameleon/"
    "complete-hsk-vocabulary/main/complete.min.json"
)

_cache: dict[str, dict[str, str]] | None = None
_auto_best_entry: dict[str, tuple[str, str]] | None = None


def _is_cjk(word: str) -> bool:
    return all("\u4e00" <= ch <= "\u9fff" for ch in word)


def _load_hsk_vocab() -> list[dict]:
    """Load HSK dataset from local cache, downloading once when missing."""
    if HSK_VOCAB_PATH.exists():
        with open(HSK_VOCAB_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []

    try:
        with urlopen(HSK_VOCAB_URL, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except (TimeoutError, URLError, OSError):
        return []

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    HSK_VOCAB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HSK_VOCAB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    return data


def _extract_entry_fields(entry: dict) -> tuple[str, int | None, str]:
    """Extract (word, frequency, meaning) from minified or full schema."""
    word = entry.get("s") or entry.get("simplified") or ""
    freq = entry.get("q") or entry.get("frequency")

    meaning = ""
    forms = entry.get("f") or entry.get("forms")
    if isinstance(forms, list) and forms:
        first_form = forms[0]
        if isinstance(first_form, dict):
            meanings = first_form.get("m") or first_form.get("meanings")
            if isinstance(meanings, list) and meanings and isinstance(meanings[0], str):
                meaning = meanings[0]

    if not isinstance(word, str):
        return "", None, ""
    if isinstance(freq, str):
        try:
            freq = int(freq)
        except ValueError:
            freq = None
    if not isinstance(freq, int):
        freq = None

    return word, freq, meaning


def _iter_2char_candidates(word: str) -> list[str]:
    """Return 2-character candidates from a word.

    - If already 2 chars, returns that word.
    - If longer, returns contiguous 2-char slices.
    """
    if len(word) == 2:
        return [word]
    if len(word) < 2:
        return []
    return [word[i : i + 2] for i in range(len(word) - 1)]


def _build_auto_index() -> dict[str, tuple[str, str]]:
    """Build best 2-char example per hanzi using HSK frequency ranking.

    Lower rank value means more common usage.
    """
    best: dict[str, tuple[str, int, bool, str]] = {}

    for entry in _load_hsk_vocab():
        if not isinstance(entry, dict):
            continue

        word, freq, meaning = _extract_entry_fields(entry)
        if not word:
            continue
        rank = freq if freq is not None else 1_000_000_000
        has_rank = freq is not None

        for candidate in _iter_2char_candidates(word):
            if len(candidate) != 2 or not _is_cjk(candidate):
                continue
            candidate_meaning = meaning if candidate == word else ""

            for ch in set(candidate):
                prev = best.get(ch)
                if prev is None:
                    best[ch] = (candidate, rank, has_rank, candidate_meaning)
                    continue

                _, prev_rank, prev_has_rank, _ = prev
                if has_rank and not prev_has_rank:
                    best[ch] = (candidate, rank, has_rank, candidate_meaning)
                elif has_rank == prev_has_rank and rank < prev_rank:
                    best[ch] = (candidate, rank, has_rank, candidate_meaning)

    return {ch: (word, meaning) for ch, (word, _, _, meaning) in best.items()}


def _lookup_auto(hanzi: str) -> tuple[str, str]:
    global _auto_best_entry
    if _auto_best_entry is None:
        _auto_best_entry = _build_auto_index()
    return _auto_best_entry.get(hanzi, ("", ""))


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

    # Auto fallback (common 2-char HSK word by frequency ranking).
    auto_word, auto_meaning = _lookup_auto(hanzi)
    if auto_word:
        return auto_word, auto_meaning

    return "", ""


def save_examples(examples: dict[str, dict]) -> None:
    """Write the example words file."""
    EXAMPLE_WORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EXAMPLE_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(examples, f, ensure_ascii=False, indent=2)
