"""Reusable reporting helpers derived from note data."""

from __future__ import annotations

import re

from .model import CharacterNote


def heisig_index(note: CharacterNote) -> int | None:
    match = re.search(r"\d+", note.heisig_num)
    return int(match.group(0)) if match else None


def filter_from_rsh(notes: list[CharacterNote], start_rsh: int) -> list[CharacterNote]:
    return [note for note in notes if (heisig_index(note) or 0) >= start_rsh]


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
        ("Example Word", "example_word"),
        ("Example Meaning", "example_meaning"),
        ("Example Pinyin", "example_pinyin"),
        ("Example Audio", "example_audio"),
        ("Stroke Order", "stroke_order"),
        ("Heisig №", "heisig_num"),
        ("Lesson", "lesson"),
        ("Mnemonic", "mnemonic"),
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
        if note.example_word and not note.example_pinyin:
            issues.append(f"#{index} ({note.hanzi}): example word without example pinyin")
        if note.example_audio and not note.example_pinyin:
            issues.append(f"#{index} ({note.hanzi}): example audio without example pinyin")

    return issues
