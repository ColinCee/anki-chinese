"""Build the Anki deck package from note data and card files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import genanki

from .config import (
    CARDS_DIR,
    DECK_ID,
    DECK_NAME,
    DECK_OUTPUT_DIR,
    FIELDS,
    GENERATED_AUDIO_DIR,
    MODEL_ID,
    MODEL_NAME,
)
from .notes.model import CharacterNote


def _read_card_file(name: str) -> str:
    path = CARDS_DIR / name
    return path.read_text(encoding="utf-8")


def _build_model() -> genanki.Model:
    css = _read_card_file("style.css")
    tone_script = _read_card_file("tone_script.html")

    return genanki.Model(
        MODEL_ID,
        MODEL_NAME,
        fields=[{"name": field_name} for field_name in FIELDS],
        sort_field_index=FIELDS.index("HeisigNum"),
        templates=[
            {
                "name": "Recognition",
                "qfmt": _read_card_file("recognition_front.html"),
                "afmt": _read_card_file("recognition_back.html") + tone_script,
            },
            {
                "name": "Listening",
                "qfmt": _read_card_file("recall_front.html"),
                "afmt": _read_card_file("recall_back.html") + tone_script,
            },
        ],
        css=css,
    )


class _StableNote(genanki.Note):
    """Note subclass with a stable GUID based on hanzi only."""

    def __init__(self, hanzi: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.guid = genanki.guid_for("chinese-rsh", hanzi)  # type: ignore[assignment]


def build_deck(notes: list[CharacterNote]) -> Path:
    model = _build_model()
    deck = genanki.Deck(DECK_ID, DECK_NAME)

    for note in notes:
        tag = note.lesson.replace(" ", "_") if note.lesson else ""
        anki_note = _StableNote(
            hanzi=note.hanzi,
            model=model,
            fields=note.to_fields_list(),
            tags=[tag] if tag else [],
        )
        deck.add_note(anki_note)

    media_files: list[str] = []
    if GENERATED_AUDIO_DIR.exists():
        media_files = [str(path) for path in GENERATED_AUDIO_DIR.glob("*.mp3")]

    DECK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DECK_OUTPUT_DIR / "chinese_rsh.apkg"

    package = genanki.Package(deck)
    package.media_files = media_files
    package.write_to_file(str(output_path))
    return output_path
