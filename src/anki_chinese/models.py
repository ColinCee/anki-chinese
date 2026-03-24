"""Backward-compatible exports for note models and note persistence."""

from .notes.model import CharacterNote, apply_overrides, load_overrides
from .notes.store import JsonNoteStore, load_notes, save_notes

__all__ = [
    "CharacterNote",
    "JsonNoteStore",
    "apply_overrides",
    "load_notes",
    "load_overrides",
    "save_notes",
]
