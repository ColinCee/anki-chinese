"""
Enrichment pipeline — takes parsed notes and fills in missing data.

Does NOT generate audio — that's a separate step because it requires
Azure credentials and costs money.
"""

from __future__ import annotations

from pypinyin.contrib.tone_convert import to_normal
from rich.progress import track

from ..config import OVERRIDES_PATH
from ..data_sources import (
    lookup_example,
    lookup_jyutping,
    lookup_pinyin,
    lookup_pinyin_word,
)
from ..models import CharacterNote, apply_overrides, load_overrides


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


def _reading_from_example(note: CharacterNote) -> str:
    if not note.example_word or not note.example_pinyin:
        return ""

    syllables = note.example_pinyin.split()
    if len(syllables) != len(note.example_word):
        return ""

    target_syllables = [
        syllables[index]
        for index, ch in enumerate(note.example_word)
        if ch == note.hanzi
    ]
    if not target_syllables:
        return ""

    normalized = [
        to_normal(syllable).lower().replace("u:", "v") for syllable in target_syllables
    ]
    unique = list(dict.fromkeys(normalized))
    if len(unique) == 1:
        return target_syllables[0]
    return ""


def _normalize_example_pinyin(note: CharacterNote) -> None:
    if not note.example_word or not note.example_pinyin:
        fallback = lookup_pinyin_word(note.example_word) if note.example_word else ""
        if fallback and len(fallback.split()) == len(note.example_word):
            note.example_pinyin = fallback
        return

    fallback = lookup_pinyin_word(note.example_word)
    if not fallback or len(fallback.split()) != len(note.example_word):
        return

    if len(note.example_pinyin.split()) != len(note.example_word):
        note.example_pinyin = fallback
        return

    current = [
        to_normal(syllable).lower().replace("u:", "v")
        for syllable in note.example_pinyin.split()
    ]
    inferred = [
        to_normal(syllable).lower().replace("u:", "v") for syllable in fallback.split()
    ]
    if current != inferred:
        note.example_pinyin = fallback


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
                )
                if word:
                    note.example_word = word
                    note.example_meaning = meaning
                    note.example_pinyin = example_pinyin

        if note.example_word and not note.example_pinyin:
            note.example_pinyin = lookup_pinyin_word(note.example_word)
        _normalize_example_pinyin(note)

        example_reading = _reading_from_example(note)

        # ── Pinyin (usage-first) ─────────────────────────────────
        if example_reading and "pinyin" not in override_fields:
            note.pinyin = example_reading
            _clear_usage_review(note)
        elif not note.pinyin:
            py, is_polyphonic = lookup_pinyin(note.hanzi)
            note.pinyin = py
            if is_polyphonic:
                _set_usage_review(
                    note,
                    f"Polyphonic character — no usage-derived reading found, "
                    f"defaulted to '{py}' — verify manually",
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

        # ── Apply manual overrides (always last) ──────────────────
        note = apply_overrides(note, overrides)

        if note.example_word and not note.example_pinyin:
            note.example_pinyin = lookup_pinyin_word(note.example_word)
        _normalize_example_pinyin(note)

        example_reading = _reading_from_example(note)
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
