"""
Manual example-word overrides loader.

Reads data/example_words.json — a hand-curated dict of
{hanzi: {"word": "...", "meaning": "...", "pinyin": "..."}} that always wins over any
auto-detected example in the lookup chain.

Format:
    {
        "早": {"word": "早安", "meaning": "good morning", "pinyin": "zǎo ān"},
        "行": {"word": "银行", "meaning": "bank", "pinyin": "yín háng"}
    }
"""

from __future__ import annotations

import json
from pathlib import Path

_cache: dict[str, dict[str, str]] | None = None
_loaded_path: Path | None = None


def load_example_overrides(path: Path) -> dict[str, dict[str, str]]:
    """Load manual example-word overrides from *path*, cached after first read."""
    global _cache, _loaded_path
    if _cache is not None and _loaded_path == path:
        return _cache

    if not path.exists():
        _cache = {}
        _loaded_path = path
        return _cache

    with open(path, encoding="utf-8") as f:
        data: dict[str, dict[str, str]] = json.load(f)

    _cache = data
    _loaded_path = path
    return _cache


def save_example_overrides(examples: dict[str, dict], path: Path) -> None:
    """Write example overrides back to *path*."""
    global _cache, _loaded_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(examples, f, ensure_ascii=False, indent=2)
    # Invalidate cache so the next read picks up the new data
    _cache = None
    _loaded_path = None
