"""Canonical structured character records used to build the Anki deck."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .model import CharacterNote, Curriculum

SOURCE_SCHEMA_VERSION = 1
_CONTENT_FIELDS = (
    "hanzi",
    "meaning",
    "pinyin",
    "jyutping",
    "sentence",
    "sentence_pinyin",
    "sentence_english",
    "stroke_order",
    "story",
)


def _content_from_note(note: CharacterNote) -> dict[str, str]:
    return {field_name: str(getattr(note, field_name)) for field_name in _CONTENT_FIELDS}


def _validate_notes(notes: list[CharacterNote], path: Path) -> None:
    seen: set[str] = set()
    for note in notes:
        if not note.hanzi:
            raise ValueError(f"Canonical source contains an empty Hanzi: {path}")
        if note.hanzi in seen:
            raise ValueError(f"Duplicate canonical character {note.hanzi!r}: {path}")
        seen.add(note.hanzi)


def source_record_from_note(note: CharacterNote) -> dict[str, Any]:
    """Serialize authored character content and curriculum metadata."""

    return {
        "hanzi": note.hanzi,
        "content": {
            field_name: value
            for field_name, value in _content_from_note(note).items()
            if field_name != "hanzi"
        },
        "curriculum": note.curriculum.to_dict(),
    }


def _legacy_record_to_note(record: dict[str, Any]) -> CharacterNote:
    """Read the pre-schema flat JSON shape during migration."""

    values = {field_name: str(record.get(field_name, "")) for field_name in _CONTENT_FIELDS}
    curriculum = Curriculum.from_legacy(
        heisig_num=str(record.get("heisig_num", "")),
        lesson=str(record.get("lesson", "")),
    )
    return CharacterNote(
        hanzi=values["hanzi"],
        meaning=values["meaning"],
        pinyin=values["pinyin"],
        jyutping=values["jyutping"],
        sentence=values["sentence"],
        sentence_pinyin=values["sentence_pinyin"],
        sentence_english=values["sentence_english"],
        stroke_order=values["stroke_order"],
        story=values["story"],
        curriculum=curriculum,
        heisig_num=str(record.get("heisig_num", "")),
        lesson=str(record.get("lesson", "")),
    )


def note_from_source_record(record: dict[str, Any]) -> CharacterNote:
    """Deserialize a canonical record, accepting the legacy flat shape."""

    if "content" not in record:
        return _legacy_record_to_note(record)

    content = record.get("content")
    if not isinstance(content, dict):
        raise ValueError("Canonical character record content must be an object.")

    curriculum_data = record.get("curriculum", {})
    if not isinstance(curriculum_data, dict):
        raise ValueError("Canonical character record curriculum must be an object.")

    hanzi = str(record.get("hanzi", "")).strip()
    values = {
        field_name: str(content.get(field_name, ""))
        for field_name in _CONTENT_FIELDS
        if field_name != "hanzi"
    }
    curriculum = Curriculum.from_dict(curriculum_data)
    return CharacterNote(
        hanzi=hanzi,
        meaning=values["meaning"],
        pinyin=values["pinyin"],
        jyutping=values["jyutping"],
        sentence=values["sentence"],
        sentence_pinyin=values["sentence_pinyin"],
        sentence_english=values["sentence_english"],
        stroke_order=values["stroke_order"],
        story=values["story"],
        curriculum=curriculum,
        heisig_num=str(curriculum.rsh_number or ""),
        lesson=curriculum.lesson,
    )


@dataclass
class CharacterSourceStore:
    """Read and atomically write the canonical character source file."""

    path: Path

    def exists(self) -> bool:
        return self.path.is_file()

    def load(self) -> list[CharacterNote]:
        with self.path.open(encoding="utf-8") as file:
            payload = json.load(file)

        if not isinstance(payload, dict):
            raise ValueError(f"Canonical source must be an object: {self.path}")
        version = payload.get("schema_version")
        if version != SOURCE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported canonical source schema {version!r}; "
                f"expected {SOURCE_SCHEMA_VERSION}."
            )
        records = payload.get("records")
        if not isinstance(records, list):
            raise ValueError(f"Canonical source records must be a list: {self.path}")

        notes = [note_from_source_record(record) for record in records]
        _validate_notes(notes, self.path)
        return notes

    def save(self, notes: list[CharacterNote]) -> None:
        _validate_notes(notes, self.path)
        records = [source_record_from_note(note) for note in notes]
        payload = {
            "schema_version": SOURCE_SCHEMA_VERSION,
            "records": records,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            delete=False,
        ) as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
            temporary_path = Path(file.name)
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, self.path)


def migrate_notes_to_source(path: Path, notes: list[CharacterNote]) -> None:
    """Write parsed legacy notes into the canonical source format."""

    CharacterSourceStore(path).save(notes)


def update_source_record(
    path: Path,
    hanzi: str,
    updates: dict[str, Any],
) -> CharacterNote:
    """Update authored fields in one canonical source record."""

    store = CharacterSourceStore(path)
    notes = store.load()
    note = next((candidate for candidate in notes if candidate.hanzi == hanzi), None)
    if note is None:
        raise KeyError(f"{hanzi} is not in {path}")
    sentence_fields = {"sentence", "sentence_pinyin", "sentence_english"}
    changed_sentence_fields = sentence_fields.intersection(updates)
    if changed_sentence_fields and changed_sentence_fields != sentence_fields:
        raise ValueError(
            "sentence, sentence_pinyin, and sentence_english must be supplied together"
        )
    for field_name, value in updates.items():
        if field_name in {"sentence_audio", "mandarin_audio", "cantonese_audio"}:
            continue
        if not hasattr(note, field_name):
            raise ValueError(f"Unsupported source record field: {field_name}")
        setattr(note, field_name, str(value))
    store.save(notes)
    return note


def add_source_record(path: Path, note: CharacterNote) -> None:
    """Append one new canonical record, rejecting duplicate Hanzi."""

    store = CharacterSourceStore(path)
    notes = store.load() if store.exists() else []
    if any(existing.hanzi == note.hanzi for existing in notes):
        raise ValueError(f"{note.hanzi} is already in {path}")
    notes.append(note)
    store.save(notes)


def default_custom_curriculum(
    *,
    lesson: str = "",
    origin: str = "manual",
    collection: str = "",
) -> Curriculum:
    return Curriculum(
        track="custom",
        rsh_number=None,
        lesson=lesson,
        origin=origin,
        collection=collection,
    )


def validate_track(value: str) -> Literal["rsh", "custom"]:
    if value not in {"rsh", "custom"}:
        raise ValueError("track must be either 'rsh' or 'custom'")
    return value  # type: ignore[return-value]


def is_single_hanzi(value: str) -> bool:
    """Return whether a value is one CJK unified ideograph."""

    if len(value) != 1:
        return False
    codepoint = ord(value)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
    )
