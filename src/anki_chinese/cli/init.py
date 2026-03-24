"""`anki-chinese init` command."""

from __future__ import annotations

from pathlib import Path

import typer

from ..audio.files import (
    expected_cantonese_audio_tag,
    expected_example_audio_tag,
    expected_mandarin_audio_tag,
)
from ..notes.model import CharacterNote
from .app import AppRuntime
from .ui import report_init_summary, report_review_items


_PRESERVE_FIELDS = (
    "mandarin_audio",
    "cantonese_audio",
    "example_pinyin",
    "example_audio",
    "mnemonic",
)


def _restore_cached_fields(
    notes: list[CharacterNote],
    previous_notes: list[CharacterNote],
    *,
    is_valid_audio_tag,
) -> tuple[dict[str, CharacterNote], int]:
    prev_by_hanzi = {note.hanzi: note for note in previous_notes}
    restored = 0
    for note in notes:
        previous = prev_by_hanzi.get(note.hanzi)
        if previous is None:
            continue
        for field in _PRESERVE_FIELDS:
            if field in {"example_pinyin", "example_audio"} and (
                not note.example_word or note.example_word != previous.example_word
            ):
                continue
            previous_value = getattr(previous, field)
            if getattr(note, field) or not previous_value:
                continue
            if field.endswith("_audio") and not is_valid_audio_tag(previous_value):
                continue
            setattr(note, field, previous_value)
            restored += 1
    return prev_by_hanzi, restored


def _clear_stale_audio(
    notes: list[CharacterNote],
    *,
    generated_audio_dir: Path,
    is_valid_audio_tag,
) -> int:
    stale_files: list[Path] = []
    for note in notes:
        expected_mandarin = expected_mandarin_audio_tag(note)
        if note.mandarin_audio and note.mandarin_audio != expected_mandarin:
            old_file = note.mandarin_audio.replace("[sound:", "").rstrip("]")
            stale_files.extend(
                path for path in [generated_audio_dir / old_file] if path.exists()
            )
            note.mandarin_audio = ""
        elif note.mandarin_audio and not is_valid_audio_tag(note.mandarin_audio):
            old_file = note.mandarin_audio.replace("[sound:", "").rstrip("]")
            stale_files.extend(
                path for path in [generated_audio_dir / old_file] if path.exists()
            )
            note.mandarin_audio = ""

        expected_cantonese = expected_cantonese_audio_tag(note)
        if note.cantonese_audio and note.cantonese_audio != expected_cantonese:
            old_file = note.cantonese_audio.replace("[sound:", "").rstrip("]")
            stale_files.extend(
                path for path in [generated_audio_dir / old_file] if path.exists()
            )
            note.cantonese_audio = ""
        elif note.cantonese_audio and not is_valid_audio_tag(note.cantonese_audio):
            old_file = note.cantonese_audio.replace("[sound:", "").rstrip("]")
            stale_files.extend(
                path for path in [generated_audio_dir / old_file] if path.exists()
            )
            note.cantonese_audio = ""

        expected_example = expected_example_audio_tag(note)
        if note.example_audio and note.example_audio != expected_example:
            old_file = note.example_audio.replace("[sound:", "").rstrip("]")
            stale_files.extend(
                path for path in [generated_audio_dir / old_file] if path.exists()
            )
            note.example_audio = ""
        elif note.example_audio and not is_valid_audio_tag(note.example_audio):
            old_file = note.example_audio.replace("[sound:", "").rstrip("]")
            stale_files.extend(
                path for path in [generated_audio_dir / old_file] if path.exists()
            )
            note.example_audio = ""

    removed_stale_files = 0
    for path in stale_files:
        try:
            path.unlink()
            removed_stale_files += 1
        except OSError:
            pass
    return removed_stale_files


def run_init(
    runtime: AppRuntime,
    input_file: Path,
    *,
    skip_examples: bool = False,
) -> list[CharacterNote]:
    runtime.console.print(f"[blue]Parsing[/blue] {input_file} ...")
    notes = runtime.parse_deck_export(input_file)
    runtime.console.print(f"  [green]✓[/green] {len(notes)} notes parsed")

    previous_notes = runtime.note_store.load() if runtime.note_store.exists() else []
    prev_by_hanzi, restored = _restore_cached_fields(
        notes,
        previous_notes,
        is_valid_audio_tag=runtime.tts_provider.is_valid_audio_tag,
    )
    if restored:
        runtime.console.print(
            f"  [green]✓[/green] Restored {restored} fields from previous data"
        )

    runtime.console.print("[blue]Enriching[/blue] ...")
    notes = runtime.enrich_notes(notes, skip_examples=skip_examples)

    removed_stale_files = _clear_stale_audio(
        notes,
        generated_audio_dir=runtime.generated_audio_dir,
        is_valid_audio_tag=runtime.tts_provider.is_valid_audio_tag,
    )
    if removed_stale_files:
        runtime.console.print(
            f"  [yellow]⚠[/yellow] Removed {removed_stale_files} stale audio files"
        )

    report_init_summary(
        runtime.console,
        notes=notes,
        prev_by_hanzi=prev_by_hanzi,
        restored_fields=restored,
        removed_stale_files=removed_stale_files,
    )
    report_review_items(runtime.console, notes)

    runtime.note_store.save(notes)
    runtime.console.print(f"[green]✓[/green] Saved → {runtime.note_store.path}")
    return notes


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command()
    def init(
        input_file: Path = typer.Option(
            runtime.source_deck_path,
            "--input",
            "-i",
            help="Anki text export to parse.",
        ),
        skip_examples: bool = typer.Option(
            False,
            "--skip-examples",
            help="Skip example-word lookup.",
        ),
    ) -> None:
        """Parse source deck export and enrich with pinyin, jyutping, examples."""
        run_init(runtime, input_file, skip_examples=skip_examples)
