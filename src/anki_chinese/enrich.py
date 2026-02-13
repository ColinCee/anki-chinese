"""
Enrichment pipeline — takes parsed notes and fills in missing data.
"""

from __future__ import annotations

from rich.progress import track

from .models import CharacterNote, apply_overrides, load_overrides
from .pinyin_lookup import lookup_pinyin
from .jyutping_lookup import lookup_jyutping
from .examples import lookup_example
from .config import OVERRIDES_PATH


def enrich_notes(
    notes: list[CharacterNote],
    *,
    skip_examples: bool = False,
) -> list[CharacterNote]:
    """Fill in missing pinyin, jyutping, and examples.

    Does NOT generate audio — that's a separate step because it requires
    Azure credentials and costs money.
    """
    overrides = load_overrides(OVERRIDES_PATH)
    enriched: list[CharacterNote] = []

    for note in track(notes, description="Enriching notes..."):
        # ── Pinyin ────────────────────────────────────────────────
        if not note.pinyin:
            py, needs_review = lookup_pinyin(note.hanzi)
            note.pinyin = py
            if needs_review:
                note.needs_review = True
                note.review_reason = (
                    f"Polyphonic character — verify pinyin '{py}' "
                    f"matches keyword '{note.keyword}'"
                )
        else:
            # Even if we have pinyin, check if it's polyphonic
            _, needs_review = lookup_pinyin(note.hanzi, existing=note.pinyin)
            if needs_review:
                note.needs_review = True
                note.review_reason = (
                    f"Polyphonic — existing pinyin '{note.pinyin}', "
                    f"verify it matches keyword '{note.keyword}'"
                )

        # ── Jyutping ─────────────────────────────────────────────
        if not note.jyutping:
            jp, needs_review = lookup_jyutping(note.hanzi)
            note.jyutping = jp
            if needs_review and not note.needs_review:
                note.needs_review = True
                note.review_reason = f"No jyutping found for '{note.hanzi}'"

        # ── Example word ──────────────────────────────────────────
        if not skip_examples and not note.example_word:
            word, meaning = lookup_example(note.hanzi)
            note.example_word = word
            note.example_meaning = meaning

        # ── Apply manual overrides (always last) ──────────────────
        note = apply_overrides(note, overrides)

        enriched.append(note)

    return enriched
