"""`anki-chinese radicals` command."""

from __future__ import annotations

from enum import StrEnum

import typer
from rich.table import Table

from ..radicals import analyze_radical_exposure
from .app import AppRuntime


class RadicalScope(StrEnum):
    deck = "deck"
    learned = "learned"


def run_radicals(
    runtime: AppRuntime,
    *,
    scope: RadicalScope = RadicalScope.deck,
    min_seen: int = 1,
    limit: int = 0,
) -> None:
    notes = runtime.note_store.load()
    scope_chars: set[str] | None = None

    if scope == RadicalScope.learned:
        scope_chars = runtime.load_learned_hanzi(runtime.source_deck_path)
        if not scope_chars:
            runtime.console.print(
                "[yellow]⚠[/yellow] No learned characters found in the source deck export."
            )
            return

    report = analyze_radical_exposure(
        notes,
        runtime.hsk_vocab_path,
        scope_chars=scope_chars,
        min_seen=min_seen,
        limit=limit,
    )

    if not report.rows:
        runtime.console.print("[yellow]No radical exposure rows matched the filters.[/yellow]")
        return

    table = Table(
        title=(
            f"Primary radicals · {scope.value} · "
            f"{report.matched_characters}/{report.total_characters} characters matched"
        )
    )
    table.add_column("Radical", style="cyan", no_wrap=True)
    table.add_column("Nickname")
    table.add_column("Meaning")
    table.add_column("Seen", justify="right")
    table.add_column("Priority")
    table.add_column("Examples")

    for row in report.rows:
        priority_style = "green" if row.priority == "learn now" else "yellow"
        table.add_row(
            row.radical,
            row.nickname,
            row.meaning,
            str(row.count),
            f"[{priority_style}]{row.priority}[/{priority_style}]",
            " ".join(row.examples),
        )

    runtime.console.print(table)
    runtime.console.print(
        f"[dim]{report.total_radicals} primary radicals found. "
        f"{report.unmatched_characters} characters had no local HSK radical match. "
        "Use --min-seen 2 or --min-seen 3 for a tighter study list.[/dim]"
    )


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command()
    def radicals(
        scope: RadicalScope = typer.Option(
            RadicalScope.deck,
            "--scope",
            help="Analyze all saved deck characters or only learned characters from the source export.",
        ),
        min_seen: int = typer.Option(
            1,
            "--min-seen",
            min=1,
            help="Only show radicals seen at least this many times.",
        ),
        limit: int = typer.Option(0, "--limit", "-n", min=0, help="Maximum rows to show."),
    ) -> None:
        """Show primary radicals encountered in saved notes."""
        run_radicals(runtime, scope=scope, min_seen=min_seen, limit=limit)
