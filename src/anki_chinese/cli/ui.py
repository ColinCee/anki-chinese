"""Shared Rich UI helpers for CLI commands."""

from __future__ import annotations

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from ..notes.model import CharacterNote
from ..notes.report import flagged_notes


def format_audio_task_labels(tasks: list[str]) -> str:
    labels = {
        "mandarin": "Mandarin",
        "cantonese": "Cantonese",
        "example": "Example",
        "sentence": "Sentence",
    }
    return ", ".join(labels[task] for task in tasks if task in labels)


def create_audio_progress(console: Console) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TextColumn("[dim]{task.fields[current]}[/dim]"),
        console=console,
    )


def report_review_items(console: Console, notes: list[CharacterNote]) -> None:
    review = flagged_notes(notes)
    if not review:
        return
    console.print(f"\n[yellow]⚠ {len(review)} notes need review:[/yellow]")
    for note in review[:15]:
        console.print(f"  {note.hanzi} ({note.keyword}): {note.review_reason}")
    if len(review) > 15:
        console.print(f"  … and {len(review) - 15} more")
    console.print("[dim]Run 'anki-chinese review' to see details and verify them.[/dim]")


def report_init_summary(
    console: Console,
    *,
    notes: list[CharacterNote],
    prev_by_hanzi: dict[str, CharacterNote],
    restored_fields: int,
    removed_stale_files: int,
) -> None:
    prev_hanzi = set(prev_by_hanzi)
    added = [note.hanzi for note in notes if note.hanzi not in prev_hanzi]
    removed = sorted(prev_hanzi - {note.hanzi for note in notes})
    changed_existing = 0
    tracked_fields = (
        "keyword",
        "pinyin",
        "jyutping",
        "example_word",
        "example_meaning",
        "example_pinyin",
        "mandarin_audio",
        "cantonese_audio",
        "example_audio",
        "story",
    )
    for note in notes:
        previous = prev_by_hanzi.get(note.hanzi)
        if previous and any(
            getattr(note, field) != getattr(previous, field)
            for field in tracked_fields
        ):
            changed_existing += 1

    console.print("\n[bold]Init Summary[/bold]")
    console.print(f"  [green]•[/green] {len(notes)} notes ready")
    if added:
        preview = ", ".join(added[:12])
        suffix = "" if len(added) <= 12 else f" … +{len(added) - 12} more"
        console.print(
            f"  [green]•[/green] {len(added)} new characters: {preview}{suffix}"
        )
    if changed_existing:
        console.print(
            f"  [green]•[/green] {changed_existing} existing characters updated"
        )
    if removed:
        preview = ", ".join(removed[:12])
        suffix = "" if len(removed) <= 12 else f" … +{len(removed) - 12} more"
        console.print(
            f"  [yellow]•[/yellow] {len(removed)} characters removed: {preview}{suffix}"
        )
    if restored_fields:
        console.print(f"  [green]•[/green] {restored_fields} cached fields reused")
    if removed_stale_files:
        console.print(
            f"  [yellow]•[/yellow] {removed_stale_files} stale audio files removed"
        )


def report_audio_summary(
    console: Console,
    *,
    processed: int,
    total: int,
    repaired: dict[str, int],
    synced: dict[str, int],
    changed_chars: list[str],
) -> None:
    repaired_total = sum(repaired.values())
    synced_total = sum(synced.values())
    console.print("\n[bold]Audio Summary[/bold]")
    console.print(f"  [green]•[/green] {processed}/{total} notes processed")
    if repaired_total or synced_total:
        if repaired_total:
            console.print(f"  [green]•[/green] {repaired_total} new audio files generated")
        if synced_total:
            console.print(
                f"  [green]•[/green] {synced_total} existing audio files linked to notes"
            )

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Audio Type")
        table.add_column("Generated", justify="right")
        table.add_column("Linked Existing", justify="right")
        table.add_row("Mandarin", str(repaired["mandarin"]), str(synced["mandarin"]))
        table.add_row("Cantonese", str(repaired["cantonese"]), str(synced["cantonese"]))
        table.add_row("Sentence", str(repaired["sentence"]), str(synced["sentence"]))
        console.print(table)
    if changed_chars:
        preview = ", ".join(changed_chars[:12])
        suffix = "" if len(changed_chars) <= 12 else f" … +{len(changed_chars) - 12} more"
        console.print(f"  [green]•[/green] Updated characters: {preview}{suffix}")


def review_table(flagged: list[CharacterNote]) -> Table:
    table = Table(title=f"Notes Needing Review · {len(flagged)} flagged", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Hanzi", style="bold", width=4)
    table.add_column("Pinyin", width=8)
    table.add_column("Keyword", width=18)
    table.add_column("Heisig", width=6)
    table.add_column("Reason", style="dim")

    for index, note in enumerate(flagged, 1):
        table.add_row(
            str(index),
            note.hanzi,
            note.pinyin,
            note.keyword,
            note.heisig_num,
            note.review_reason,
        )

    return table
