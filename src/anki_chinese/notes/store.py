"""Persistence helpers for serialized note data."""

from __future__ import annotations

import json
from pathlib import Path

from .model import CharacterNote


class JsonNoteStore:
    """Tiny repository for loading and saving `CharacterNote` lists."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> list[CharacterNote]:
        return load_notes(self.path)

    def save(self, notes: list[CharacterNote]) -> None:
        save_notes(notes, self.path)


def save_notes(notes: list[CharacterNote], path: Path) -> None:
    """Save enriched notes to JSON for inspection / manual editing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump([note.to_dict() for note in notes], file, ensure_ascii=False, indent=2)


def load_notes(path: Path) -> list[CharacterNote]:
    """Load previously saved notes."""
    with open(path, encoding="utf-8") as file:
        return [CharacterNote.from_dict(row) for row in json.load(file)]
