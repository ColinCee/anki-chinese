"""`anki-chinese audio` command."""

from __future__ import annotations

from pathlib import Path

import typer

from ..audio import (
    TTSRateLimitError,
    collect_orphaned_audio,
    expected_cantonese_audio_tag,
    expected_mandarin_audio_tag,
    expected_sentence_audio_tag,
)
from ..audio.state import (
    AudioDeckState,
    audio_generation_profiles,
    backfill_audio_manifest,
    build_audio_deck_state,
    load_audio_manifest,
    save_audio_manifest,
)
from ..notes import CharacterNote, filter_from_rsh, heisig_index
from ..workflows.pipeline_state import record_stage
from .app import AppRuntime
from .ui import create_audio_progress, format_audio_task_labels, report_audio_summary

AudioCleanKind = str
PendingAudio = tuple[CharacterNote, list[str], set[str]]


def _collect_pending_audio(
    targets: list[CharacterNote],
    *,
    force: bool,
    deck_state: AudioDeckState,
    learned: set[str],
    limit: int,
) -> list[PendingAudio]:
    """Filter targets to notes needing audio, prioritize learned, apply limit."""
    target_by_hanzi = {note.hanzi: note for note in targets}
    task_map: dict[str, list[str]] = {note.hanzi: [] for note in targets}
    force_map: dict[str, set[str]] = {note.hanzi: set() for note in targets}
    for requirement in deck_state.requirements:
        if requirement.hanzi not in target_by_hanzi:
            continue
        if force:
            if requirement.expected is not None:
                task_map[requirement.hanzi].append(requirement.kind)
        elif requirement.needs_generation:
            task_map[requirement.hanzi].append(requirement.kind)
            if requirement.force_generation:
                force_map[requirement.hanzi].add(requirement.kind)

    pending: list[PendingAudio] = []
    for hanzi, tasks in task_map.items():
        if tasks:
            pending.append((target_by_hanzi[hanzi], tasks, force_map[hanzi]))

    if learned:
        pending.sort(key=lambda pair: pair[0].hanzi not in learned)

    if limit > 0:
        pending = pending[:limit]

    return pending


def _save_current_audio_manifest(runtime: AppRuntime, notes: list[CharacterNote]) -> None:
    profiles = audio_generation_profiles(runtime.tts_provider, runtime.sentence_tts_provider)
    save_audio_manifest(
        runtime.audio_manifest_path,
        backfill_audio_manifest(
            notes,
            profiles=profiles,
            generated_audio_dir=runtime.generated_audio_dir,
        ),
    )


def load_current_audio_deck_state(
    runtime: AppRuntime,
    notes: list[CharacterNote],
) -> AudioDeckState:
    profiles = audio_generation_profiles(runtime.tts_provider, runtime.sentence_tts_provider)
    return build_audio_deck_state(
        notes,
        profiles=profiles,
        generated_audio_dir=runtime.generated_audio_dir,
        manifest=load_audio_manifest(runtime.audio_manifest_path),
    )


def _generate_one_note(
    note: CharacterNote,
    tasks: list[str],
    runtime: AppRuntime,
    *,
    force: bool,
    force_tasks: set[str] | None = None,
) -> dict[str, int]:
    """Generate audio for a single note, returning per-type counts of new files."""
    generated: dict[str, int] = {}
    force_tasks = force_tasks or set()

    if "mandarin" in tasks and note.pinyin:
        expected = expected_mandarin_audio_tag(note)
        was_cached = bool(expected and runtime.tts_provider.is_valid_audio_tag(expected))
        effective_force = force or "mandarin" in force_tasks
        note.mandarin_audio = runtime.tts_provider.generate_mandarin(
            note.hanzi,
            note.pinyin,
            force=effective_force,
        )
        generated["mandarin"] = 0 if was_cached and not effective_force else 1

    if "cantonese" in tasks and note.jyutping:
        expected = expected_cantonese_audio_tag(note)
        was_cached = bool(expected and runtime.tts_provider.is_valid_audio_tag(expected))
        effective_force = force or "cantonese" in force_tasks
        note.cantonese_audio = runtime.tts_provider.generate_cantonese(
            note.hanzi,
            note.jyutping,
            force=effective_force,
        )
        generated["cantonese"] = 0 if was_cached and not effective_force else 1

    if "sentence" in tasks and note.sentence:
        provider = runtime.sentence_tts_provider or runtime.tts_provider
        expected = expected_sentence_audio_tag(note)
        was_cached = bool(expected and provider.is_valid_audio_tag(expected))
        effective_force = force or "sentence" in force_tasks
        note.sentence_audio = provider.generate_sentence_audio(
            note.hanzi,
            note.sentence,
            force=effective_force,
        )
        generated["sentence"] = 0 if was_cached and not effective_force else 1

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
    audio_state = load_current_audio_deck_state(runtime, targets)
    pending = _collect_pending_audio(
        targets,
        force=force,
        deck_state=audio_state,
        learned=learned,
        limit=limit,
    )

    if not pending:
        runtime.console.print(f"[green]✓[/green] Audio already up to date for {len(targets)} notes")
        _save_current_audio_manifest(runtime, notes)
        record_stage(
            runtime.pipeline_state_path,
            "audio",
            inputs={"enriched": runtime.note_store.path},
            outputs={"generated_audio": runtime.generated_audio_dir},
        )
        return notes

    if learned:
        learned_count = sum(1 for n, _, _ in pending if n.hanzi in learned)
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
        for index, (note, tasks, force_tasks) in enumerate(pending, 1):
            progress.update(
                task_id,
                current=f"{note.hanzi} ({note.meaning}) · {format_audio_task_labels(tasks)}",
            )
            try:
                generated = _generate_one_note(
                    note,
                    tasks,
                    runtime,
                    force=force,
                    force_tasks=force_tasks,
                )
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
                _save_current_audio_manifest(runtime, notes)
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
    _save_current_audio_manifest(runtime, notes)
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
    else:
        record_stage(
            runtime.pipeline_state_path,
            "audio",
            inputs={"enriched": runtime.note_store.path},
            outputs={"generated_audio": runtime.generated_audio_dir},
        )

    return notes


def _audio_file_matches_kind(filename: str, kind: AudioCleanKind) -> bool:
    if kind == "all":
        return True
    if kind == "sentence":
        return filename.startswith("cmn_sentence_")
    if kind == "mandarin":
        return filename.startswith("cmn_") and not filename.startswith("cmn_sentence_")
    if kind == "cantonese":
        return filename.startswith("yue_")
    return False


def run_audio_clean(
    runtime: AppRuntime,
    *,
    apply: bool = False,
    kind: AudioCleanKind = "all",
) -> list[str]:
    """Report or remove generated audio files no note currently references."""
    notes = runtime.note_store.load()
    orphans = [
        path
        for path in collect_orphaned_audio(notes, runtime.generated_audio_dir)
        if _audio_file_matches_kind(path.name, kind)
    ]
    if not orphans:
        runtime.console.print("[green]✓[/green] No orphaned generated audio files")
        return []

    runtime.console.print(f"[yellow]⚠[/yellow] {len(orphans)} orphaned generated audio files")
    for path in orphans[:20]:
        runtime.console.print(f"  • {path.name}")
    if len(orphans) > 20:
        runtime.console.print(f"  … and {len(orphans) - 20} more")

    if not apply:
        runtime.console.print("[dim]Dry run only. Re-run with --apply to delete them.[/dim]")
        return [path.name for path in orphans]

    removed: list[Path] = []
    for path in orphans:
        path.unlink()
        removed.append(path)
    runtime.console.print(f"[green]✓[/green] Removed {len(removed)} orphaned audio files")
    return [path.name for path in removed]


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

    @app.command("audio-clean")
    def audio_clean(
        apply: bool = typer.Option(
            False,
            "--apply",
            help="Delete orphaned files. Without this, only shows a dry run.",
        ),
        kind: str = typer.Option(
            "all",
            "--kind",
            help="Audio kind to clean: all, sentence, mandarin, or cantonese.",
        ),
    ) -> None:
        """Remove generated audio files that are no longer referenced by notes."""
        if kind not in {"all", "sentence", "mandarin", "cantonese"}:
            runtime.console.print("[red]✗[/red] --kind must be all, sentence, mandarin, or cantonese")
            raise typer.Exit(1)
        run_audio_clean(runtime, apply=apply, kind=kind)
