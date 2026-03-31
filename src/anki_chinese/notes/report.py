"""Reusable reporting helpers derived from note data."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

import csv
import re
from pathlib import Path

from .model import CharacterNote


def heisig_index(note: CharacterNote) -> int | None:
    match = re.search(r"\d+", note.heisig_num)
    return int(match.group(0)) if match else None


def filter_from_rsh(notes: list[CharacterNote], start_rsh: int) -> list[CharacterNote]:
    return [note for note in notes if (heisig_index(note) or 0) >= start_rsh]


def load_learned_hanzi(path: Path) -> set[str]:
    """Load the set of learned characters from an Anki text export."""
    if not path.exists():
        return set()
    learned: set[str] = set()
    with open(path, encoding="utf-8") as f:
        lines = [line for line in f if not line.startswith("#") and line.strip()]
    for row in csv.reader(lines, delimiter="\t"):
        if len(row) > 3 and row[3].strip():
            learned.add(row[3].strip())
    return learned


def prioritize_learned(
    notes: list[CharacterNote], learned: set[str]
) -> list[CharacterNote]:
    """Sort notes so learned characters come first, preserving relative order."""
    first = [n for n in notes if n.hanzi in learned]
    rest = [n for n in notes if n.hanzi not in learned]
    return first + rest


def flagged_notes(notes: list[CharacterNote]) -> list[CharacterNote]:
    return [note for note in notes if note.needs_review]


def coverage_rows(notes: list[CharacterNote]) -> list[tuple[str, int, int, float]]:
    rows: list[tuple[str, int, int, float]] = []
    for label, attr in [
        ("Hanzi", "hanzi"),
        ("Keyword", "keyword"),
        ("Pinyin", "pinyin"),
        ("Jyutping", "jyutping"),
        ("Mandarin Audio", "mandarin_audio"),
        ("Cantonese Audio", "cantonese_audio"),
        ("Sentence", "sentence"),
        ("Sentence Pinyin", "sentence_pinyin"),
        ("Sentence English", "sentence_english"),
        ("Sentence Audio", "sentence_audio"),
        ("Stroke Order", "stroke_order"),
        ("Heisig №", "heisig_num"),
        ("Lesson", "lesson"),
        ("Story", "story"),
    ]:
        filled = sum(1 for note in notes if getattr(note, attr))
        missing = len(notes) - filled
        pct = filled / len(notes) * 100 if notes else 0
        rows.append((label, filled, missing, pct))
    return rows


def validation_issues(notes: list[CharacterNote]) -> list[str]:
    issues: list[str] = []
    seen: dict[str, int] = {}

    for index, note in enumerate(notes):
        if note.hanzi in seen:
            issues.append(f"Duplicate '{note.hanzi}' at #{seen[note.hanzi]} and #{index}")
        seen[note.hanzi] = index

        if not note.hanzi:
            issues.append(f"#{index}: missing hanzi")
        if not note.keyword:
            issues.append(f"#{index} ({note.hanzi}): missing keyword")
        if not note.pinyin:
            issues.append(f"#{index} ({note.hanzi}): missing pinyin")
        if note.mandarin_audio and not note.pinyin:
            issues.append(f"#{index} ({note.hanzi}): audio without pinyin")
        if note.cantonese_audio and not note.jyutping:
            issues.append(f"#{index} ({note.hanzi}): audio without jyutping")

    return issues
