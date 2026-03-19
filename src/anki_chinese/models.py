"""
Data models.  CharacterNote is the single source of truth for one character.
Everything flows through this: parser → enrichment → deck generation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, asdict
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
    example_word: str = ""
    example_meaning: str = ""
    example_pinyin: str = ""
    example_audio: str = ""
    stroke_order: str = ""
    heisig_num: str = ""
    lesson: str = ""
    mnemonic: str = ""

    # ── Internal bookkeeping (not exported to Anki) ───────────────────
    needs_review: bool = field(default=False, repr=False)
    review_reason: str = field(default="", repr=False)

    def to_fields_list(self) -> list[str]:
        """Return field values in the order expected by the genanki model."""
        return [
            self.hanzi,
            self.keyword,
            self.pinyin,
            self.jyutping,
            self.mandarin_audio,
            self.cantonese_audio,
            self.example_word,
            self.example_meaning,
            self.example_pinyin,
            self.example_audio,
            self.stroke_order,
            self.heisig_num,
            self.lesson,
            self.mnemonic,
        ]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CharacterNote:
        # Only pass keys that are actual fields on the dataclass
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


# ── Overrides ─────────────────────────────────────────────────────────


def load_overrides(path: Path) -> dict[str, dict[str, Any]]:
    """Load per-character overrides.  Keys are hanzi, values are dicts of
    field names to override values.  Example:

        {
            "行": {"pinyin": "xíng", "jyutping": "haang4", "keyword": "go"},
            "了": {"pinyin": "le"}
        }

    Any field on CharacterNote can be overridden.
    """
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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


# ── Serialization ─────────────────────────────────────────────────────


def save_notes(notes: list[CharacterNote], path: Path) -> None:
    """Save enriched notes to JSON for inspection / manual editing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([n.to_dict() for n in notes], f, ensure_ascii=False, indent=2)


def load_notes(path: Path) -> list[CharacterNote]:
    """Load previously saved notes."""
    with open(path, encoding="utf-8") as f:
        return [CharacterNote.from_dict(d) for d in json.load(f)]
