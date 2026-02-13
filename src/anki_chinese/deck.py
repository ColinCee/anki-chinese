"""
Deck generator — builds the .apkg file using genanki.

Reads card templates from the templates/ directory so you can edit
the HTML/CSS/JS without touching Python code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import genanki

from .config import (
    MODEL_ID,
    DECK_ID,
    DECK_NAME,
    MODEL_NAME,
    FIELDS,
    TEMPLATE_DIR,
    OUTPUT_DIR,
    GENERATED_MEDIA_DIR,
)
from .models import CharacterNote


def _read_template(name: str) -> str:
    """Read a template file from the templates/ directory."""
    path = TEMPLATE_DIR / name
    return path.read_text(encoding="utf-8")


def _build_model() -> genanki.Model:
    """Build the genanki Model from config + template files."""
    css = _read_template("style.css")

    return genanki.Model(
        MODEL_ID,
        MODEL_NAME,
        fields=[{"name": f} for f in FIELDS],
        templates=[
            {
                "name": "Recognition",
                "qfmt": _read_template("recognition_front.html"),
                "afmt": _read_template("recognition_back.html"),
            },
            {
                "name": "Recall",
                "qfmt": _read_template("recall_front.html"),
                "afmt": _read_template("recall_back.html"),
            },
        ],
        css=css,
    )


class _StableNote(genanki.Note):
    """Note subclass with a stable GUID based on hanzi character only.

    This means you can regenerate the deck, change any field, and Anki
    will update the existing note instead of creating a duplicate.
    """

    def __init__(self, hanzi: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.guid = genanki.guid_for("chinese-rsh", hanzi)  # type: ignore[assignment]


def build_deck(notes: list[CharacterNote]) -> Path:
    """Build a .apkg file from a list of CharacterNote objects.

    Returns the path to the generated .apkg file.
    """
    model = _build_model()
    deck = genanki.Deck(DECK_ID, DECK_NAME)

    for note in notes:
        # Anki tags cannot contain spaces — replace with underscores
        tag = note.lesson.replace(" ", "_") if note.lesson else ""
        anki_note = _StableNote(
            hanzi=note.hanzi,
            model=model,
            fields=note.to_fields_list(),
            tags=[tag] if tag else [],
        )
        deck.add_note(anki_note)

    # Collect all generated media files
    media_files: list[str] = []
    if GENERATED_MEDIA_DIR.exists():
        media_files = [
            str(p) for p in GENERATED_MEDIA_DIR.iterdir() if p.suffix == ".mp3"
        ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "chinese_rsh.apkg"

    package = genanki.Package(deck)
    package.media_files = media_files
    package.write_to_file(str(output_path))

    return output_path
