"""
Jyutping lookup using ToJyutping as primary, pycantonese as optional fallback.

pycantonese has a broken dependency on pkg_resources (removed in Python 3.13),
so we make it optional and use ToJyutping as the reliable primary source.
"""

from __future__ import annotations

import re
from types import ModuleType

import ToJyutping

# Try importing pycantonese — it may fail on Python 3.13+
_pycantonese: ModuleType | None = None
try:
    import pycantonese as _pycantonese_mod

    _pycantonese = _pycantonese_mod
except (ImportError, ModuleNotFoundError):
    pass


def _parse_tojyutping_result(result: str | None) -> list[tuple[str, str]]:
    """Parse ToJyutping output like '一(jat1)二(ji6)' into [('一', 'jat1'), ...]."""
    if not result:
        return []
    return re.findall(r"(.)\(([a-z]+\d)\)", result)


def lookup_jyutping(hanzi: str, existing: str = "") -> tuple[str, bool]:
    """Look up jyutping for a single character.

    Returns:
        (jyutping_string, needs_review)

    Strategy:
        1. If we have an existing jyutping from the old deck, keep it
        2. Try ToJyutping (reliable, large dictionary)
        3. Try pycantonese if available (corpus-based)
        4. If nothing found, flag for review
    """
    if existing:
        return existing, False

    # Primary: ToJyutping
    try:
        result = ToJyutping.get_jyutping(hanzi)
        parsed = _parse_tojyutping_result(result)
        if parsed:
            return parsed[0][1], False
    except Exception:
        pass

    # Fallback: pycantonese (if available)
    if _pycantonese is not None:
        try:
            results = _pycantonese.characters_to_jyutping(hanzi)
            if results and results[0][1]:
                return results[0][1], False
        except Exception:
            pass

    return "", True  # Nothing found — needs manual entry


def lookup_jyutping_word(word: str) -> str:
    """Look up jyutping for a multi-character word."""
    try:
        result = ToJyutping.get_jyutping(word)
        parsed = _parse_tojyutping_result(result)
        if parsed:
            parts = [jp for _, jp in parsed]
            if parts:
                return " ".join(parts)
    except Exception:
        pass

    if _pycantonese is not None:
        try:
            results = _pycantonese.characters_to_jyutping(word)
            if results:
                parts = [jp for _, jp in results if jp]
                if len(parts) == len(word):
                    return " ".join(parts)
        except Exception:
            pass

    return ""
