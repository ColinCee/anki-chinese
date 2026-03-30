"""Enrichment pipeline — fill in pinyin, jyutping, and examples."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

from rich.progress import track

from ..config import OVERRIDES_PATH
from ..data_sources import (
    lookup_example,
    lookup_jyutping,
    lookup_pinyin,
    lookup_pinyin_word,
)
from .model import CharacterNote, apply_overrides, load_overrides
from .pronunciation import normalize_example_pinyin, reading_from_example


def _set_usage_review(note: CharacterNote, reason: str) -> None:
    note.needs_review = True
    note.review_reason = reason


def _clear_usage_review(note: CharacterNote) -> None:
    usage_prefixes = (
        "Could not derive a single reading",
        "Polyphonic character — no usage-derived reading found",
    )
    if note.review_reason.startswith(usage_prefixes):
        note.needs_review = False
        note.review_reason = ""


def enrich_notes(
    notes: list[CharacterNote],
    *,
    skip_examples: bool = False,
) -> list[CharacterNote]:
    """Fill in missing pinyin, jyutping, and examples for each note."""
    overrides = load_overrides(OVERRIDES_PATH)
    enriched: list[CharacterNote] = []

    for note in track(notes, description="Enriching notes..."):
        override_fields = overrides.get(note.hanzi, {})

        if not note.jyutping:
            jyutping, needs_review = lookup_jyutping(note.hanzi)
            note.jyutping = jyutping
            if needs_review and not note.needs_review:
                note.needs_review = True
                note.review_reason = f"No jyutping found for '{note.hanzi}'"

        if not skip_examples and (
            not note.example_word
            or (note.example_word and not note.example_meaning)
            or (note.example_word and not note.example_pinyin)
        ):
            word, meaning, example_pinyin = lookup_example(note.hanzi)
            if word:
                note.example_word = word
                note.example_meaning = meaning
                note.example_pinyin = example_pinyin

        if note.example_word and not note.example_pinyin:
            note.example_pinyin = lookup_pinyin_word(note.example_word)
        normalize_example_pinyin(note, lookup_pinyin_word)

        example_reading = reading_from_example(note)

        if example_reading and "pinyin" not in override_fields:
            note.pinyin = example_reading
            _clear_usage_review(note)
        elif not note.pinyin:
            pinyin, is_polyphonic = lookup_pinyin(note.hanzi)
            note.pinyin = pinyin
            if is_polyphonic:
                _set_usage_review(
                    note,
                    f"Polyphonic character — no usage-derived reading found, "
                    f"defaulted to '{pinyin}' — verify manually",
                )
        elif (
            note.example_word
            and note.example_pinyin
            and "pinyin" not in override_fields
            and not note.needs_review
        ):
            _set_usage_review(
                note,
                f"Could not derive a single reading for '{note.hanzi}' from "
                f"example '{note.example_word}' / '{note.example_pinyin}'",
            )

        note = apply_overrides(note, overrides)

        if note.example_word and not note.example_pinyin:
            note.example_pinyin = lookup_pinyin_word(note.example_word)
        normalize_example_pinyin(note, lookup_pinyin_word)

        example_reading = reading_from_example(note)
        if example_reading and "pinyin" not in override_fields:
            note.pinyin = example_reading
            _clear_usage_review(note)
        elif (
            note.example_word
            and note.example_pinyin
            and "pinyin" not in override_fields
            and not note.needs_review
        ):
            _set_usage_review(
                note,
                f"Could not derive a single reading for '{note.hanzi}' from "
                f"example '{note.example_word}' / '{note.example_pinyin}'",
            )

        enriched.append(note)

    return enriched
