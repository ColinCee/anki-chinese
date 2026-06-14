"""CLI composition root."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path

import typer
from rich.console import Console

from ..audio import TTSProvider, build_tts_provider
from ..config import (
    DECK_OUTPUT_DIR,
    ENRICHED_PATH,
    GENERATED_AUDIO_DIR,
    HSK_VOCAB_PATH,
    OVERRIDES_PATH,
    SAMPLE_AUDIO_DIR,
    SONG_LYRICS_DIR,
    SOURCE_DECK_PATH,
)
from ..deck import build_deck
from ..notes import (
    CharacterNote,
    JsonNoteStore,
    enrich_notes,
    load_deck_hanzi_from_apkg,
    load_learned_hanzi_from_apkg,
    parse_apkg,
)
from ..tui.dashboard import run_dashboard


@dataclass
class AppRuntime:
    source_deck_path: Path
    overrides_path: Path
    song_lyrics_dir: Path
    hsk_vocab_path: Path
    note_store: JsonNoteStore
    generated_audio_dir: Path
    sample_audio_dir: Path
    deck_output_path: Path
    parse_deck_export: Callable[[Path], list[CharacterNote]]
    load_learned_hanzi: Callable[[Path], set[str]]
    load_deck_hanzi: Callable[[Path], set[str]]
    enrich_notes: Callable[..., list[CharacterNote]]
    build_deck: Callable[[list[CharacterNote]], Path]
    tts_provider_factory: Callable[[Path], TTSProvider]
    tts_provider: TTSProvider
    sentence_tts_provider: TTSProvider | None = None
    console: Console = field(default_factory=Console)


def _build_sentence_tts_provider(generated_audio_dir: Path) -> TTSProvider:
    """MiniMax for sentence audio — better quality for longer text."""
    return build_tts_provider(generated_audio_dir=generated_audio_dir, provider_name="minimax")


def build_runtime() -> AppRuntime:
    return AppRuntime(
        source_deck_path=SOURCE_DECK_PATH,
        overrides_path=OVERRIDES_PATH,
        song_lyrics_dir=SONG_LYRICS_DIR,
        hsk_vocab_path=HSK_VOCAB_PATH,
        note_store=JsonNoteStore(ENRICHED_PATH),
        generated_audio_dir=GENERATED_AUDIO_DIR,
        sample_audio_dir=SAMPLE_AUDIO_DIR,
        deck_output_path=DECK_OUTPUT_DIR / "chinese_rsh.apkg",
        parse_deck_export=parse_apkg,
        load_learned_hanzi=load_learned_hanzi_from_apkg,
        load_deck_hanzi=load_deck_hanzi_from_apkg,
        enrich_notes=enrich_notes,
        build_deck=build_deck,
        tts_provider_factory=lambda generated_audio_dir: build_tts_provider(
            generated_audio_dir=generated_audio_dir
        ),
        tts_provider=build_tts_provider(generated_audio_dir=GENERATED_AUDIO_DIR),
        sentence_tts_provider=_build_sentence_tts_provider(GENERATED_AUDIO_DIR),
    )


def create_app(runtime: AppRuntime | None = None) -> typer.Typer:
    runtime = runtime or build_runtime()
    app = typer.Typer(
        name="anki-chinese",
        help="Generate Anki decks for Chinese (Mandarin + Cantonese) using Heisig RSH.",
        no_args_is_help=False,
    )

    @app.callback(invoke_without_command=True)
    def main(ctx: typer.Context) -> None:
        """Open the dashboard in a terminal, or show help in non-interactive contexts."""
        if ctx.invoked_subcommand is not None:
            return
        if sys.stdin.isatty() and sys.stdout.isatty():
            run_dashboard(runtime)
            return
        typer.echo(ctx.get_help())

    audio_command = import_module(".audio", __package__)
    activate_command = import_module(".activate", __package__)
    build_command = import_module(".build", __package__)
    dashboard_command = import_module(".dashboard", __package__)
    init_command = import_module(".init", __package__)
    keywords_command = import_module(".keywords", __package__)
    radicals_command = import_module(".radicals", __package__)
    sentences_command = import_module(".sentences", __package__)
    songs_command = import_module(".songs", __package__)
    status_command = import_module(".status", __package__)
    sync_command = import_module(".sync", __package__)
    test_tts_command = import_module(".test_tts", __package__)

    activate_command.register(app, runtime)
    dashboard_command.register(app, runtime)
    init_command.register(app, runtime)
    sentences_command.register(app, runtime)
    songs_command.register(app, runtime)
    keywords_command.register(app, runtime)
    radicals_command.register(app, runtime)
    audio_command.register(app, runtime)
    build_command.register(app, runtime)
    status_command.register(app, runtime)
    sync_command.register(app, runtime)
    test_tts_command.register(app, runtime)
    return app


app = create_app()
