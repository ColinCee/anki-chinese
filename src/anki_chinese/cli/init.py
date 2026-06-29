"""`anki-chinese init` command."""

from __future__ import annotations

from pathlib import Path

import typer

from ..audio import (
    expected_cantonese_audio_tag,
    expected_mandarin_audio_tag,
    expected_sentence_audio_tag,
)
from ..notes import CharacterNote
from ..workflows.pipeline_state import record_stage
from .app import AppRuntime
from .ui import report_init_summary, report_review_items

_PRESERVE_FIELDS = (
    "mandarin_audio",
    "cantonese_audio",
    "sentence",
    "sentence_pinyin",
    "sentence_english",
    "sentence_audio",
    "story",
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
        restored_sentence = False
        for field in _PRESERVE_FIELDS:
            current_value = getattr(note, field)
            previous_value = getattr(previous, field)
            if field.endswith("_audio") and not is_valid_audio_tag(previous_value):
                continue
            if field.endswith("_audio"):
                if current_value and is_valid_audio_tag(current_value):
                    continue
                if not current_value and not previous_value:
                    continue
            elif current_value or not previous_value:
                continue
            setattr(note, field, previous_value)
            if field == "sentence":
                restored_sentence = True
            restored += 1
        # If the previous note had a Gemini-generated sentence, its meaning
        # and pinyin are the contextual values for that restored sentence.
        if restored_sentence and previous.meaning:
            note.meaning = previous.meaning
            restored += 1
        if restored_sentence and previous.pinyin:
            note.pinyin = previous.pinyin
            restored += 1
    return prev_by_hanzi, restored


def _clear_stale_audio(
    notes: list[CharacterNote],
    *,
    generated_audio_dir: Path,
    is_valid_audio_tag,
) -> int:
    stale_files: list[Path] = []

    def _check_stale(note: CharacterNote, tag_attr: str, expected: str) -> None:
        tag = getattr(note, tag_attr)
        if not tag:
            return
        if tag != expected or not is_valid_audio_tag(tag):
            old_file = tag.replace("[sound:", "").rstrip("]")
            path = generated_audio_dir / old_file
            if path.exists():
                stale_files.append(path)
            setattr(note, tag_attr, "")

    for note in notes:
        _check_stale(note, "mandarin_audio", expected_mandarin_audio_tag(note))
        _check_stale(note, "cantonese_audio", expected_cantonese_audio_tag(note))
        _check_stale(note, "sentence_audio", expected_sentence_audio_tag(note))

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
        runtime.console.print(f"  [green]✓[/green] Restored {restored} fields from previous data")

    runtime.console.print("[blue]Enriching[/blue] ...")
    notes = runtime.enrich_notes(notes)

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
    record_stage(
        runtime.pipeline_state_path,
        "init",
        inputs={
            "source_deck": input_file,
        },
        outputs={},
    )
    runtime.console.print(f"[green]✓[/green] Saved → {runtime.note_store.path}")
    return notes


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command()
    def init(
        input_file: Path = typer.Option(
            runtime.source_deck_path,
            "--input",
            "-i",
            help="Anki .apkg export to parse.",
        ),
    ) -> None:
        """Parse source .apkg deck export and enrich with pinyin and jyutping."""
        run_init(runtime, input_file)
