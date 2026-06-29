"""Enrichment pipeline — fill in pinyin and jyutping."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

from rich.progress import track

from ..data_sources import (
    lookup_jyutping,
    lookup_pinyin,
)
from .model import CharacterNote


def _set_usage_review(note: CharacterNote, reason: str) -> None:
    note.needs_review = True
    note.review_reason = reason


def enrich_notes(
    notes: list[CharacterNote],
) -> list[CharacterNote]:
    """Fill in missing pinyin and jyutping for each note."""
    enriched: list[CharacterNote] = []

    for note in track(notes, description="Enriching notes..."):
        if not note.jyutping:
            jyutping, needs_review = lookup_jyutping(note.hanzi)
            note.jyutping = jyutping
            if needs_review and not note.needs_review:
                note.needs_review = True
                note.review_reason = f"No jyutping found for '{note.hanzi}'"

        if not note.pinyin:
            pinyin, is_polyphonic = lookup_pinyin(note.hanzi)
            note.pinyin = pinyin
            if is_polyphonic:
                _set_usage_review(
                    note,
                    f"Polyphonic character — no usage-derived reading found, "
                    f"defaulted to '{pinyin}' — verify manually",
                )

        enriched.append(note)

    return enriched
