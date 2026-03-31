"""
+Data models and note-level override helpers.
"""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any


@dataclass
class CharacterNote:
    """One character = one note = two cards."""

    hanzi: str = ""
    keyword: str = ""
    pinyin: str = ""
    jyutping: str = ""
    mandarin_audio: str = ""
    cantonese_audio: str = ""

    sentence: str = ""
    sentence_pinyin: str = ""
    sentence_english: str = ""

    sentence_audio: str = ""
    stroke_order: str = ""
    heisig_num: str = ""
    lesson: str = ""
    story: str = ""

    needs_review: bool = field(default=False, repr=False)
    review_reason: str = field(default="", repr=False)

    def to_fields_list(self) -> list[str]:
        return [
            self.hanzi,
            self.keyword,
            self.pinyin,
            self.jyutping,
            self.mandarin_audio,
            self.cantonese_audio,
            self.stroke_order,
            self.heisig_num,
            self.lesson,
            self.story,
            self.sentence_audio,
            self.sentence,
            self.sentence_pinyin,
            self.sentence_english,
        ]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CharacterNote:
        valid = {field_.name for field_ in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in valid})


def load_overrides(path: Path) -> dict[str, dict[str, Any]]:
    """Load per-character overrides."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def apply_overrides(
    note: CharacterNote, overrides: dict[str, dict[str, Any]]
) -> CharacterNote:
    """Apply manual overrides for a character, if any exist."""
    if note.hanzi not in overrides:
        return note
    for key, value in overrides[note.hanzi].items():
        if hasattr(note, key):
            setattr(note, key, value)
    return note
