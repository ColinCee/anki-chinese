"""`anki-chinese status` and `anki-chinese review` commands."""

from __future__ import annotations

import typer
from rich.table import Table

from ..config import LEARNED_CHARS_PATH
from ..notes import coverage_rows, flagged_notes, load_learned_hanzi, validation_issues
from .app import AppRuntime
from .ui import review_table


def run_status(runtime: AppRuntime) -> None:
    notes = runtime.note_store.load()

    table = Table(title=f"Coverage · {len(notes)} notes")
    table.add_column("Field", style="cyan")
    table.add_column("Filled", justify="right")
    table.add_column("Missing", justify="right")
    table.add_column("%", justify="right")

    for label, filled, missing, pct in coverage_rows(notes):
        color = "green" if pct > 90 else "yellow" if pct > 50 else "red"
        table.add_row(label, str(filled), str(missing), f"[{color}]{pct:.0f}%[/{color}]")

    runtime.console.print(table)

    # Learned characters progress
    learned = load_learned_hanzi(LEARNED_CHARS_PATH)
    if learned:
        learned_notes = [n for n in notes if n.hanzi in learned]
        total = len(learned_notes)
        with_sentence = sum(1 for n in learned_notes if n.sentence)
        with_audio = sum(1 for n in learned_notes if n.sentence_audio)
        runtime.console.print(
            f"\n[bold]Learned characters[/bold] · {total} of {len(learned)}"
        )
        sent_color = "green" if with_sentence == total else "yellow"
        audio_color = "green" if with_audio == total else "yellow"
        runtime.console.print(
            f"  Sentences: [{sent_color}]{with_sentence}/{total}[/{sent_color}]  "
            f"Audio: [{audio_color}]{with_audio}/{total}[/{audio_color}]"
        )

    issues = validation_issues(notes)
    review_count = len(flagged_notes(notes))

    if issues:
        runtime.console.print(f"\n[red]✗ {len(issues)} issues:[/red]")
        for issue in issues[:20]:
            runtime.console.print(f"  • {issue}")
        if len(issues) > 20:
            runtime.console.print(f"  … and {len(issues) - 20} more")
    else:
        runtime.console.print("\n[green]✓ No issues[/green]")

    if review_count:
        runtime.console.print(f"[yellow]⚠ {review_count} notes flagged for review[/yellow]")
        runtime.console.print("[dim]Run 'anki-chinese review' to inspect and verify them.[/dim]")


def run_review(runtime: AppRuntime) -> None:
    notes = runtime.note_store.load()
    flagged = flagged_notes(notes)

    if not flagged:
        runtime.console.print("[green]✓ No notes need review.[/green]")
        return

    runtime.console.print(review_table(flagged))
    runtime.console.print(
        "\n[bold]To fix:[/bold] add corrections to [bold]data/manual/overrides.json[/bold]:"
    )
    runtime.console.print('  [dim]{ "行": { "pinyin": "xíng" } }[/dim]')
    runtime.console.print("Then re-run [bold]anki-chinese init[/bold].\n")


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command()
    def status() -> None:
        """Show coverage stats and check for problems."""
        run_status(runtime)

    @app.command()
    def review() -> None:
        """Inspect notes flagged for review."""
        run_review(runtime)
