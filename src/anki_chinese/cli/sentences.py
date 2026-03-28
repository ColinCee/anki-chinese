"""`anki-chinese sentences` command."""

from __future__ import annotations

import os

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

from ..notes.model import CharacterNote
from ..notes.report import filter_from_rsh
from .app import AppRuntime


def run_sentences(
    runtime: AppRuntime,
    *,
    char: str = "",
    limit: int = 0,
    start_rsh: int = 0,
    force: bool = False,
) -> list[CharacterNote]:
    """Generate example sentences for notes that don't have them yet."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        runtime.console.print(
            "[yellow]⚠[/yellow] GEMINI_API_KEY not set — skipping sentence generation.\n"
            "  Set it in .env or environment to enable."
        )
        return runtime.note_store.load()

    from ..sentences import SentenceGenerator
    generator = SentenceGenerator(api_key=api_key)

    notes = runtime.note_store.load()
    targets = notes

    if char:
        targets = [n for n in notes if n.hanzi == char]
        if not targets:
            runtime.console.print(f"[red]✗[/red] Character '{char}' not found")
            raise typer.Exit(1)
    elif start_rsh > 0:
        targets = filter_from_rsh(notes, start_rsh)
        if limit > 0:
            targets = targets[:limit]
    elif limit > 0:
        targets = targets[:limit]

    if not force:
        targets = [n for n in targets if not n.sentence]

    if not targets:
        runtime.console.print(
            "[green]✓[/green] All notes already have sentences"
        )
        return notes

    runtime.console.print(
        f"[blue]Generating sentences[/blue] for {len(targets)} notes ..."
    )

    generated = 0
    failed = 0
    retried = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=runtime.console,
    ) as progress:
        task_id = progress.add_task("Sentences", total=len(targets))
        for note in targets:
            progress.update(task_id, description=f"[cyan]{note.hanzi}[/cyan]")
            try:
                result = generator.generate(note.hanzi)
                note.sentence = result.sentence
                note.sentence_pinyin = result.pinyin
                note.sentence_english = result.english
                note.sentence_keyword = result.keyword
                if result.valid:
                    generated += 1
                else:
                    failed += 1
                if result.error:
                    retried += 1
            except Exception as exc:
                runtime.console.print(
                    f"  [red]✗[/red] {note.hanzi}: {exc}"
                )
                failed += 1
            progress.advance(task_id)

    runtime.note_store.save(notes)
    runtime.console.print(
        f"[green]✓[/green] Generated {generated} sentences"
        + (f", {retried} retried" if retried else "")
        + (f", [red]{failed} failed[/red]" if failed else "")
    )
    return notes


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command()
    def sentences(
        char: str = typer.Option("", "--char", "-c", help="Generate for one character only."),
        limit: int = typer.Option(0, "--limit", "-n", help="Max notes to process."),
        start_rsh: int = typer.Option(0, "--from-rsh", help="Start from RSH number."),
        force: bool = typer.Option(False, "--force", "-f", help="Regenerate even if sentence exists."),
    ) -> None:
        """Generate example sentences using Gemini AI."""
        run_sentences(runtime, char=char, limit=limit, start_rsh=start_rsh, force=force)
