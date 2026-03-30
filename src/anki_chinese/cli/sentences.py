"""`anki-chinese sentences` command."""

from __future__ import annotations

import os

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.table import Table

from ..config import LEARNED_CHARS_PATH
from ..notes.model import CharacterNote
from ..notes.report import filter_from_rsh, load_learned_hanzi, prioritize_learned
from ..sentences import SentenceResult
from .app import AppRuntime


def apply_sentence(note: CharacterNote, result: SentenceResult) -> None:
    """Write a sentence result onto a note, clearing stale audio."""
    note.sentence = result.sentence
    note.sentence_pinyin = result.pinyin
    note.sentence_english = result.english
    if result.keyword:
        note.keyword = result.keyword
    note.sentence_audio = ""


def _candidates_table(candidates: list[SentenceResult]) -> Table:
    """Build a Rich table showing numbered sentence candidates."""
    table = Table(show_header=True, show_lines=True)
    table.add_column("#", style="bold", width=3)
    table.add_column("Sentence", style="cyan")
    table.add_column("Pinyin")
    table.add_column("English")
    table.add_column("Keyword", style="green")
    table.add_column("OK", width=3)
    for i, c in enumerate(candidates, 1):
        ok = "[green]✓[/green]" if c.valid else "[red]✗[/red]"
        table.add_row(str(i), c.sentence, c.pinyin, c.english, c.keyword, ok)
    return table


def _pick_sentence(runtime: AppRuntime, generator, note: CharacterNote, count: int) -> None:
    """Generate candidates in a loop until the user picks or skips."""
    runtime.console.print(
        f"\n[blue]Generating {count} candidates for[/blue] [bold]{note.hanzi}[/bold] "
        f"({note.keyword})"
    )
    if note.sentence:
        runtime.console.print(f"  [dim]Current: {note.sentence} — {note.sentence_english}[/dim]")

    while True:
        candidates = generator.generate_candidates(note.hanzi, count=count)
        if not candidates:
            runtime.console.print("[red]✗[/red] No valid candidates generated")
            return

        runtime.console.print(_candidates_table(candidates))
        choice = typer.prompt(
            "Pick a sentence (number), or 's' to skip, 'r' to regenerate",
            default="1",
        )

        if choice.lower() == "s":
            runtime.console.print("[dim]Skipped[/dim]")
            return
        if choice.lower() == "r":
            continue

        try:
            idx = int(choice) - 1
            if not 0 <= idx < len(candidates):
                runtime.console.print("[red]Invalid choice[/red]")
                return
        except ValueError:
            runtime.console.print("[red]Invalid choice[/red]")
            return

        apply_sentence(note, candidates[idx])
        runtime.console.print(f"[green]✓[/green] Saved: {candidates[idx].sentence}")
        return


def run_sentences(
    runtime: AppRuntime,
    *,
    char: str = "",
    limit: int = 0,
    start_rsh: int = 0,
    force: bool = False,
    pick: int = 0,
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
    else:
        if start_rsh > 0:
            targets = filter_from_rsh(targets, start_rsh)
        if not force and not pick:
            targets = [n for n in targets if not n.sentence]
        # Prioritize learned characters before applying limit
        learned = load_learned_hanzi(LEARNED_CHARS_PATH)
        if learned:
            targets = prioritize_learned(targets, learned)
        if limit > 0:
            targets = targets[:limit]
        if learned:
            learned_count = sum(1 for n in targets if n.hanzi in learned)
            runtime.console.print(f"  [dim]{learned_count} learned characters prioritized[/dim]")

    if not targets:
        runtime.console.print(
            "[green]✓[/green] All notes already have sentences"
        )
        return notes

    # Interactive pick mode
    if pick > 0:
        for note in targets:
            _pick_sentence(runtime, generator, note, count=pick)
        runtime.note_store.save(notes)
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
                apply_sentence(note, result)
                # Preserve audio tag — batch mode doesn't clear it
                # (audio command handles generation separately)
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
        pick: int = typer.Option(0, "--pick", "-p", help="Generate N candidates and pick interactively."),
    ) -> None:
        """Generate example sentences using Gemini AI."""
        run_sentences(runtime, char=char, limit=limit, start_rsh=start_rsh, force=force, pick=pick)
