"""CLI composition root."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path

import typer
from rich.console import Console

from ..audio.azure import AzureTTSProvider
from ..audio.provider import TTSProvider
from ..config import ENRICHED_PATH, GENERATED_MEDIA_DIR, SOURCE_DECK_PATH, TEST_MEDIA_DIR
from ..deck import build_deck
from ..notes import CharacterNote, JsonNoteStore
from ..notes.enrich import enrich_notes
from ..notes.parser import parse_deck_export


@dataclass
class AppRuntime:
    source_deck_path: Path
    note_store: JsonNoteStore
    generated_media_dir: Path
    test_media_dir: Path
    parse_deck_export: Callable[[Path], list[CharacterNote]]
    enrich_notes: Callable[..., list[CharacterNote]]
    build_deck: Callable[[list[CharacterNote]], Path]
    tts_provider: TTSProvider
    console: Console = field(default_factory=Console)


def build_runtime() -> AppRuntime:
    return AppRuntime(
        source_deck_path=SOURCE_DECK_PATH,
        note_store=JsonNoteStore(ENRICHED_PATH),
        generated_media_dir=GENERATED_MEDIA_DIR,
        test_media_dir=TEST_MEDIA_DIR,
        parse_deck_export=parse_deck_export,
        enrich_notes=enrich_notes,
        build_deck=build_deck,
        tts_provider=AzureTTSProvider(generated_media_dir=GENERATED_MEDIA_DIR),
    )


def create_app(runtime: AppRuntime | None = None) -> typer.Typer:
    runtime = runtime or build_runtime()
    app = typer.Typer(
        name="anki-chinese",
        help="Generate Anki decks for Chinese (Mandarin + Cantonese) using Heisig RSH.",
        no_args_is_help=True,
    )

    audio_command = import_module(".audio", __package__)
    build_command = import_module(".build", __package__)
    init_command = import_module(".init", __package__)
    status_command = import_module(".status", __package__)
    test_tts_command = import_module(".test_tts", __package__)

    init_command.register(app, runtime)
    audio_command.register(app, runtime)
    build_command.register(app, runtime)
    status_command.register(app, runtime)
    test_tts_command.register(app, runtime)
    return app


app = create_app()
