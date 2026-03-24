"""
HSK vocabulary data source.

Loads the Complete HSK 3.0 vocabulary list (hsk_complete.min.json), auto-
downloading it on first use when the file is absent. Builds a per-character index so callers can ask
"what is the most common HSK word containing character X?".

Lower `q` (rank/frequency) value in the HSK data means the word appears
more frequently.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

_HSK_VOCAB_URL = (
    "https://raw.githubusercontent.com/drkameleon/"
    "complete-hsk-vocabulary/main/complete.min.json"
)

# Module-level cache
_index: dict[str, list[tuple[str, str, str]]] | None = None


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


def _normalize_pinyin(text: str) -> str:
    return " ".join(text.lower().split())


def _extract_fields(entry: dict) -> tuple[str, int | None, str, str]:
    """Return (simplified_word, frequency_rank, first_meaning, pinyin)."""
    word = entry.get("s") or entry.get("simplified") or ""
    freq = entry.get("q") or entry.get("frequency")

    meaning = ""
    pinyin = ""
    forms = entry.get("f") or entry.get("forms")
    if isinstance(forms, list) and forms:
        first_form = forms[0]
        if isinstance(first_form, dict):
            meanings = first_form.get("m") or first_form.get("meanings")
            if isinstance(meanings, list) and meanings and isinstance(meanings[0], str):
                meaning = meanings[0]
            info = first_form.get("i")
            if isinstance(info, dict):
                raw_pinyin = info.get("y")
                if isinstance(raw_pinyin, str):
                    pinyin = _normalize_pinyin(raw_pinyin)

    if not isinstance(word, str):
        return "", None, "", ""
    if isinstance(freq, str):
        try:
            freq = int(freq)
        except ValueError:
            freq = None
    if not isinstance(freq, int):
        freq = None

    return word, freq, meaning, pinyin


def build_index(path: Path) -> dict[str, list[tuple[str, str, str]]]:
    """
    Build {hanzi -> [(word, meaning, pinyin), ...]} from HSK data at *path*.

    Selection rules (in priority order):
    1. Full word ≥ 2 chars whose meaning we have (is_exact=True)
    2. Among those, lowest rank value (= highest real-world frequency)
    """
    candidates: dict[str, list[tuple[int, bool, str, str, str]]] = {}

    for entry in _load_raw(path):
        if not isinstance(entry, dict):
            continue

        word, freq, meaning, pinyin = _extract_fields(entry)
        if not word or len(word) < 2 or not _is_cjk(word):
            continue

        rank = freq if freq is not None else 1_000_000_000
        for ch in set(word):
            candidates.setdefault(ch, []).append(
                (rank, freq is not None, word, meaning, pinyin)
            )

    index: dict[str, list[tuple[str, str, str]]] = {}
    for ch, rows in candidates.items():
        rows.sort(key=lambda item: (not item[1], item[0], len(item[2]), item[2]))
        deduped: list[tuple[str, str, str]] = []
        seen: set[str] = set()
        for _, _, word, meaning, pinyin in rows:
            if word in seen:
                continue
            deduped.append((word, meaning, pinyin))
            seen.add(word)
        index[ch] = deduped

    return index


def lookup(hanzi: str, path: Path) -> list[tuple[str, str, str]]:
    """Return [(word, meaning, pinyin), ...] for *hanzi* from HSK data."""
    global _index
    if _index is None:
        _index = build_index(path)
    return _index.get(hanzi, [])
