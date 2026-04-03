"""
Public API for all data-source lookups.

Callers import from here — never from the private _*.py modules directly.
"""

from __future__ import annotations

from ._cedict import lookup_char_defs
from ._jyutping import lookup_jyutping, lookup_jyutping_word
from ._pinyin import lookup_pinyin, lookup_pinyin_word

__all__ = [
    "lookup_char_defs",
    "lookup_jyutping",
    "lookup_jyutping_word",
    "lookup_pinyin",
    "lookup_pinyin_word",
]
