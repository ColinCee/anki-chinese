"""
HSK vocabulary data source.

Loads the Complete HSK 3.0 vocabulary list (hsk_complete.min.json), auto-
downloading it on first use.  Builds a per-character index so callers can ask
"what is the most common HSK word containing character X?".

Lower `q` (rank/frequency) value in the HSK data means the word appears
more frequently.
"""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import urlopen
from pathlib import Path

_HSK_VOCAB_URL = (
    "https://raw.githubusercontent.com/drkameleon/"
    "complete-hsk-vocabulary/main/complete.min.json"
)

# Module-level cache
_index: dict[str, tuple[str, str]] | None = None


def _is_cjk(word: str) -> bool:
    return all("\u4e00" <= ch <= "\u9fff" for ch in word)


def _load_raw(path: Path) -> list[dict]:
    """Load HSK JSON from *path*, downloading once when missing."""
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []

    try:
        with urlopen(_HSK_VOCAB_URL, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except (TimeoutError, URLError, OSError):
        return []

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    return data


def _extract_fields(entry: dict) -> tuple[str, int | None, str]:
    """Return (simplified_word, frequency_rank, first_meaning)."""
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


def build_index(path: Path) -> dict[str, tuple[str, str]]:
    """
    Build {hanzi -> (best_word, meaning)} from HSK data at *path*.

    Selection rules (in priority order):
    1. Full word ≥ 2 chars whose meaning we have (is_exact=True)
    2. Among those, lowest rank value (= highest real-world frequency)
    """
    # Tuple stored per char: (word, rank, has_rank, meaning, is_exact)
    best: dict[str, tuple[str, int, bool, str, bool]] = {}

    for entry in _load_raw(path):
        if not isinstance(entry, dict):
            continue

        word, freq, meaning = _extract_fields(entry)
        if not word or len(word) < 2 or not _is_cjk(word):
            continue

        rank = freq if freq is not None else 1_000_000_000
        has_rank = freq is not None
        is_exact = True  # every HSK entry is a real word with a meaning

        for ch in set(word):
            prev = best.get(ch)
            if prev is None:
                best[ch] = (word, rank, has_rank, meaning, is_exact)
                continue

            _, prev_rank, prev_has_rank, _, prev_exact = prev

            if is_exact and not prev_exact:
                best[ch] = (word, rank, has_rank, meaning, is_exact)
            elif is_exact == prev_exact:
                if has_rank and not prev_has_rank:
                    best[ch] = (word, rank, has_rank, meaning, is_exact)
                elif has_rank == prev_has_rank and rank < prev_rank:
                    best[ch] = (word, rank, has_rank, meaning, is_exact)

    return {ch: (word, meaning) for ch, (word, _, _, meaning, _) in best.items()}


def lookup(hanzi: str, path: Path) -> tuple[str, str]:
    """Return (word, meaning) for *hanzi* from HSK data, or ("", "")."""
    global _index
    if _index is None:
        _index = build_index(path)
    return _index.get(hanzi, ("", ""))
