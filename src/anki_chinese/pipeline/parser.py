"""Backward-compatible parser exports."""

from ..notes.parser import parse_deck_export, parse_old_deck

__all__ = ["parse_deck_export", "parse_old_deck"]
