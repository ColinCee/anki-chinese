"""Note-focused modules: model, parsing, enrichment, storage, and reporting."""

from .apkg_reader import load_deck_hanzi_from_apkg, load_learned_hanzi_from_apkg, parse_apkg
from .enrich import enrich_notes
from .model import CharacterNote, apply_overrides, load_overrides
from .pronunciation import PhoneticConfuser, find_phonetic_confuser_details, find_phonetic_confusers
from .report import (
    coverage_rows,
    filter_from_rsh,
    flagged_notes,
    heisig_index,
    prioritize_learned,
    validation_issues,
)
from .store import JsonNoteStore, load_notes, save_notes

__all__ = [
    "CharacterNote",
    "JsonNoteStore",
    "PhoneticConfuser",
    "apply_overrides",
    "coverage_rows",
    "enrich_notes",
    "filter_from_rsh",
    "find_phonetic_confuser_details",
    "find_phonetic_confusers",
    "flagged_notes",
    "heisig_index",
    "load_learned_hanzi_from_apkg",
    "load_deck_hanzi_from_apkg",
    "load_notes",
    "load_overrides",
    "parse_apkg",
    "prioritize_learned",
    "save_notes",
    "validation_issues",
]
