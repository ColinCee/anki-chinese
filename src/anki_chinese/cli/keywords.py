"""`anki-chinese keywords` command."""

from __future__ import annotations

import os

import typer
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from ..notes import CharacterNote
from .app import AppRuntime


def run_keywords(
    runtime: AppRuntime,
    *,
    limit: int = 0,
    force: bool = False,
) -> list[CharacterNote]:
    """Fix meanings on notes that already have sentences."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        runtime.console.print(
            "[yellow]⚠[/yellow] GEMINI_API_KEY not set — skipping meaning fixing.\n"
            "  Set it in .env or environment to enable."
        )
        return runtime.note_store.load()

    from ..sentences import KeywordFixer

    fixer = KeywordFixer(api_key=api_key)

    notes = runtime.note_store.load()
    targets = [n for n in notes if n.sentence]

    if limit > 0:
        targets = targets[:limit]

    if not targets:
        runtime.console.print("[green]✓[/green] No notes with sentences to fix")
        return notes

    runtime.console.print(f"[blue]Fixing meanings[/blue] for {len(targets)} notes ...")

    # Build (hanzi, sentence, english) tuples
    items = [(n.hanzi, n.sentence, n.sentence_english) for n in targets]

    updated = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=runtime.console,
    ) as progress:
        task_id = progress.add_task("Keywords", total=len(targets))
        result_map = fixer.fix_batch(
            items,
            on_chunk_done=lambda n: progress.advance(task_id, n),
        )

    for note in targets:
        new_keyword = result_map.get(note.hanzi)
        if new_keyword and new_keyword != note.meaning:
            note.meaning = new_keyword
            updated += 1

    runtime.note_store.save(notes)
    runtime.console.print(f"[green]✓[/green] Updated {updated} meanings")
    return notes


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command()
    def keywords(
        limit: int = typer.Option(0, "--limit", "-n", help="Max notes to process."),
        force: bool = typer.Option(False, "--force", "-f", help="Re-fix all meanings."),
    ) -> None:
        """Fix meanings to contextual meanings using Gemini AI."""
        run_keywords(runtime, limit=limit, force=force)
