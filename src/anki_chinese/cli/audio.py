"""`anki-chinese audio` command."""

from __future__ import annotations

from collections.abc import Callable

import typer

from ..audio import (
    TTSRateLimitError,
    audio_tasks_for_note,
    expected_cantonese_audio_tag,
    expected_mandarin_audio_tag,
    expected_sentence_audio_tag,
)
from ..notes import CharacterNote, filter_from_rsh, heisig_index
from .app import AppRuntime
from .ui import create_audio_progress, format_audio_task_labels, report_audio_summary


def _collect_pending_audio(
    targets: list[CharacterNote],
    *,
    force: bool,
    is_valid_tag: Callable[[str], bool],
    learned: set[str],
    limit: int,
) -> list[tuple[CharacterNote, list[str]]]:
    """Filter targets to notes needing audio, prioritize learned, apply limit."""
    pending: list[tuple[CharacterNote, list[str]]] = []
    for note in targets:
        tasks = audio_tasks_for_note(
            note,
            force=force,
            is_valid_audio_tag_fn=is_valid_tag,
        )
        if tasks:
            pending.append((note, tasks))

    if learned:
        pending.sort(key=lambda pair: pair[0].hanzi not in learned)

    if limit > 0:
        pending = pending[:limit]

    return pending


def _generate_one_note(
    note: CharacterNote,
    tasks: list[str],
    runtime: AppRuntime,
    *,
    force: bool,
) -> dict[str, int]:
    """Generate audio for a single note, returning per-type counts of new files."""
    generated: dict[str, int] = {}

    if "mandarin" in tasks and note.pinyin:
        expected = expected_mandarin_audio_tag(note)
        was_cached = bool(expected and runtime.tts_provider.is_valid_audio_tag(expected))
        note.mandarin_audio = runtime.tts_provider.generate_mandarin(
            note.hanzi,
            note.pinyin,
            force=force,
        )
        generated["mandarin"] = 0 if was_cached and not force else 1

    if "cantonese" in tasks and note.jyutping:
        expected = expected_cantonese_audio_tag(note)
        was_cached = bool(expected and runtime.tts_provider.is_valid_audio_tag(expected))
        note.cantonese_audio = runtime.tts_provider.generate_cantonese(
            note.hanzi,
            note.jyutping,
            force=force,
        )
        generated["cantonese"] = 0 if was_cached and not force else 1

    if "sentence" in tasks and note.sentence:
        provider = runtime.sentence_tts_provider or runtime.tts_provider
        expected = expected_sentence_audio_tag(note)
        was_cached = bool(expected and provider.is_valid_audio_tag(expected))
        note.sentence_audio = provider.generate_sentence_audio(
            note.hanzi,
            note.sentence,
            force=force,
        )
        generated["sentence"] = 0 if was_cached and not force else 1

    return generated


def run_audio(
    runtime: AppRuntime,
    *,
    all_notes: list[CharacterNote] | None = None,
    char: str = "",
    limit: int = 0,
    start_rsh: int = 0,
    force: bool = False,
    fail_fast: bool = False,
) -> list[CharacterNote]:
    notes = all_notes if all_notes is not None else runtime.note_store.load()
    targets = notes

    if char:
        targets = [note for note in notes if note.hanzi == char]
        if not targets:
            runtime.console.print(f"[red]✗[/red] Character '{char}' not found")
            raise typer.Exit(1)
    elif start_rsh > 0:
        targets = filter_from_rsh(targets, start_rsh)
        if not targets:
            runtime.console.print(f"[red]✗[/red] No notes found at or after RSH #{start_rsh}")
            raise typer.Exit(1)

    learned = runtime.load_learned_hanzi(runtime.source_deck_path)
    pending = _collect_pending_audio(
        targets,
        force=force,
        is_valid_tag=runtime.tts_provider.is_valid_audio_tag,
        learned=learned,
        limit=limit,
    )

    if not pending:
        runtime.console.print(f"[green]✓[/green] Audio already up to date for {len(targets)} notes")
        return notes

    if learned:
        learned_count = sum(1 for n, _ in pending if n.hanzi in learned)
        runtime.console.print(f"  [dim]{learned_count} learned characters prioritized[/dim]")

    skipped = len(targets) - len(pending)
    runtime.console.print(f"[blue]Audio[/blue] {len(pending)} notes need updates")
    if skipped:
        runtime.console.print(f"  [dim]{skipped} notes already had valid audio[/dim]")

    failures: list[str] = []
    repaired = {"mandarin": 0, "cantonese": 0, "sentence": 0}
    synced = {"mandarin": 0, "cantonese": 0, "sentence": 0}
    changed_chars: list[str] = []

    progress = create_audio_progress(runtime.console)
    with progress:
        task_id = progress.add_task("Audio", total=len(pending), current="Preparing...")
        for index, (note, tasks) in enumerate(pending, 1):
            progress.update(
                task_id,
                current=f"{note.hanzi} ({note.meaning}) · {format_audio_task_labels(tasks)}",
            )
            try:
                generated = _generate_one_note(note, tasks, runtime, force=force)
                for kind, count in generated.items():
                    repaired[kind] += count
                    synced[kind] += 1 - count
                if generated:
                    changed_chars.append(note.hanzi)
                progress.advance(task_id)
            except TTSRateLimitError as error:
                progress.stop()
                failures.append(f"{note.hanzi} ({note.meaning}): {error}")
                runtime.note_store.save(notes)
                report_audio_summary(
                    runtime.console,
                    processed=index - 1,
                    total=len(pending),
                    repaired=repaired,
                    synced=synced,
                    changed_chars=changed_chars,
                )
                runtime.console.print(f"[yellow]⚠[/yellow] {error}")
                runtime.console.print(
                    f"[yellow]Stopped on TTS provider rate limit at {note.hanzi} "
                    f"(RSH #{heisig_index(note) or '?'}). Re-run the same audio command later.[/yellow]"
                )
                raise typer.Exit(2) from None
            except Exception as error:
                failures.append(f"{note.hanzi} ({note.meaning}): {error}")
                runtime.console.print(f"[red]✗[/red] {note.hanzi} ({note.meaning}): {error}")
                progress.advance(task_id)
                if fail_fast:
                    raise

    runtime.note_store.save(notes)
    report_audio_summary(
        runtime.console,
        processed=len(pending),
        total=len(pending),
        repaired=repaired,
        synced=synced,
        changed_chars=changed_chars,
    )
    runtime.console.print("[green]✓[/green] Audio done")
    if failures:
        runtime.console.print(
            f"[yellow]⚠ {len(failures)} notes failed during audio generation[/yellow]"
        )
        for failure in failures[:15]:
            runtime.console.print(f"  • {failure}")
        if len(failures) > 15:
            runtime.console.print(f"  … and {len(failures) - 15} more")

    return notes


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command()
    def audio(
        char: str = typer.Option(
            "",
            "--char",
            "-c",
            help="Generate audio for a single character only.",
        ),
        limit: int = typer.Option(
            0,
            "--limit",
            "-l",
            help="Process only the first N notes (0 = all).",
        ),
        start_rsh: int = typer.Option(
            0,
            "--start-rsh",
            help="Start audio generation from this Heisig/RSH number onward.",
        ),
        force: bool = typer.Option(
            False,
            "--force",
            "-f",
            help="Regenerate files that already exist.",
        ),
        fail_fast: bool = typer.Option(
            False,
            "--fail-fast",
            help="Stop immediately on first TTS error.",
        ),
    ) -> None:
        """Generate pronunciation audio via the configured TTS provider."""
        run_audio(
            runtime,
            char=char,
            limit=limit,
            start_rsh=start_rsh,
            force=force,
            fail_fast=fail_fast,
        )
