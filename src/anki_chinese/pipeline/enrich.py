"""
Enrichment pipeline — takes parsed notes and fills in missing data.

Does NOT generate audio — that's a separate step because it requires
Azure credentials and costs money.
"""

from __future__ import annotations

from rich.progress import track

from ..config import OVERRIDES_PATH
from ..data_sources import (
    lookup_example,
    lookup_jyutping,
    lookup_pinyin,
    lookup_pinyin_word,
)
from ..models import CharacterNote, apply_overrides, load_overrides


def _example_matches_primary_reading(note: CharacterNote) -> bool:
    if not note.example_word or not note.example_pinyin or not note.pinyin:
        return True

    syllables = note.example_pinyin.split()
    if len(syllables) != len(note.example_word):
        return False

    return any(
        syllables[index] == note.pinyin
        for index, ch in enumerate(note.example_word)
        if ch == note.hanzi
    )


def enrich_notes(
    notes: list[CharacterNote],
    *,
    skip_examples: bool = False,
) -> list[CharacterNote]:
    """Fill in missing pinyin, jyutping, and examples for each note."""
    overrides = load_overrides(OVERRIDES_PATH)
    enriched: list[CharacterNote] = []

    for note in track(notes, description="Enriching notes..."):
        # ── Pinyin ────────────────────────────────────────────────
        if not note.pinyin:
            py, is_polyphonic = lookup_pinyin(note.hanzi)
            note.pinyin = py
            if is_polyphonic:
                note.needs_review = True
                note.review_reason = (
                    f"Polyphonic character — no pinyin in source, "
                    f"defaulted to '{py}' — verify reading manually"
                )

        # ── Jyutping ─────────────────────────────────────────────
        if not note.jyutping:
            jp, needs_review = lookup_jyutping(note.hanzi)
            note.jyutping = jp
            if needs_review and not note.needs_review:
                note.needs_review = True
                note.review_reason = f"No jyutping found for '{note.hanzi}'"

        # ── Example word ──────────────────────────────────────────
        if not skip_examples:
            if (
                not note.example_word
                or (note.example_word and not note.example_meaning)
                or (note.example_word and not note.example_pinyin)
            ):
                word, meaning, example_pinyin = lookup_example(
                    note.hanzi,
                    preferred_pinyin=note.pinyin,
                )
                if word:
                    note.example_word = word
                    note.example_meaning = meaning
                    note.example_pinyin = example_pinyin

        if note.example_word and not note.example_pinyin:
            note.example_pinyin = lookup_pinyin_word(note.example_word)

        if (
            note.example_word
            and note.example_pinyin
            and not _example_matches_primary_reading(note)
        ):
            note.needs_review = True
            note.review_reason = (
                f"Example '{note.example_word}' uses '{note.example_pinyin}', "
                f"which does not match primary reading '{note.pinyin}'"
            )

        # ── Apply manual overrides (always last) ──────────────────
        note = apply_overrides(note, overrides)

        if note.example_word and not note.example_pinyin:
            note.example_pinyin = lookup_pinyin_word(note.example_word)

        enriched.append(note)

    return enriched
