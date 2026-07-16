"""`anki-chinese frequency` commands."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import typer
from rich.table import Table

from ..activation import AnkiConnectClient, AnkiConnectError
from ..character_frequency import (
    FrequencyDataError,
    FrequencyReport,
    build_frequency_report,
    fetch_frequency_snapshot,
    load_frequency_snapshot,
    save_frequency_snapshot,
)
from ..config import CHARACTER_FREQUENCY_PATH
from .app import AppRuntime


class FrequencyStateClient(Protocol):
    def find_studied_characters(self) -> set[str]:
        """Return characters with at least one recorded review."""
        ...

    def find_all_deck_info(self) -> tuple[list[str], set[str]]:
        """Return deck order and all character notes."""
        ...


def _default_client() -> AnkiConnectClient:
    return AnkiConnectClient(api_key=os.getenv("ANKICONNECT_API_KEY", "").strip())


def run_frequency_refresh(
    runtime: AppRuntime,
    *,
    cache_path: Path = CHARACTER_FREQUENCY_PATH,
) -> None:
    try:
        snapshot = fetch_frequency_snapshot()
        save_frequency_snapshot(snapshot, cache_path)
    except FrequencyDataError as error:
        runtime.console.print(f"[red]✗[/red] {error}")
        raise typer.Exit(2) from None

    runtime.console.print(
        f"[green]✓[/green] Cached {len(snapshot.entries):,} characters "
        f"from {snapshot.source_name}"
    )
    runtime.console.print(f"  [dim]Corpus:[/dim] {snapshot.corpus_characters:,} characters")
    runtime.console.print(f"  [dim]Source data:[/dim] {snapshot.source_last_updated}")
    runtime.console.print(f"  [dim]Cache:[/dim] {cache_path}")


def _render_report(runtime: AppRuntime, report: FrequencyReport, *, limit: int) -> None:
    runtime.console.print("[bold]Character frequency report[/bold]")
    runtime.console.print(
        f"  Reviewed at least once: {report.studied_count:,} characters"
        f" · {report.deck_covered_count:,}/{report.deck_character_count:,} in deck"
        f" ({report.deck_coverage_percent:.1f}%)"
    )
    runtime.console.print(
        f"  Corpus-weighted character coverage: {report.corpus_coverage_percent:.1f}%"
    )
    runtime.console.print(
        f"  Approximate reading band: [bold]{report.estimated_band}[/bold]"
        " [dim](character recognition only)[/dim]"
    )
    if report.studied_unranked_count:
        runtime.console.print(
            f"  [dim]{report.studied_unranked_count} reviewed characters were not in the source list[/dim]"
        )

    table = Table(title=f"Top frequency gaps in your deck · {limit}")
    table.add_column("Rank", justify="right")
    table.add_column("Character", style="cyan")
    table.add_column("Corpus count", justify="right")
    table.add_column("Cumulative", justify="right")
    for entry in report.gap_entries:
        table.add_row(
            str(entry.rank),
            entry.character,
            f"{entry.frequency:,}",
            f"{entry.cumulative_percent:.2f}%",
        )
    runtime.console.print(table)
    if report.unranked_gap_count:
        runtime.console.print(
            f"[dim]{report.unranked_gap_count} additional deck characters have no source rank.[/dim]"
        )
    runtime.console.print(
        "\n[dim]This is a corpus-weighted reading estimate, not an overall proficiency score; "
        "it does not measure listening, speaking, grammar, or active recall.[/dim]"
    )


def run_frequency_report(
    runtime: AppRuntime,
    *,
    cache_path: Path = CHARACTER_FREQUENCY_PATH,
    limit: int = 20,
    json_output: bool = False,
    client: FrequencyStateClient | None = None,
) -> FrequencyReport:
    try:
        snapshot = load_frequency_snapshot(cache_path)
    except FrequencyDataError as error:
        runtime.console.print(f"[red]✗[/red] {error}")
        raise typer.Exit(1) from None

    client = client or _default_client()
    try:
        studied = client.find_studied_characters()
        _, deck_characters = client.find_all_deck_info()
    except AnkiConnectError as error:
        runtime.console.print(f"[red]✗[/red] {error}")
        runtime.console.print("[dim]Ensure Anki is open with AnkiConnect installed.[/dim]")
        raise typer.Exit(2) from None

    report = build_frequency_report(
        snapshot,
        studied_characters=studied,
        deck_characters=deck_characters,
        limit=limit,
    )
    if json_output:
        runtime.console.print_json(data=report.to_dict(cache_path=cache_path))
    else:
        _render_report(runtime, report, limit=limit)
    return report


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    frequency_app = typer.Typer(
        name="frequency",
        help="Compare reviewed characters with a cached Mandarin frequency corpus.",
        no_args_is_help=True,
    )

    @frequency_app.command("refresh")
    def refresh_command() -> None:
        """Fetch and cache the corpus frequency list explicitly."""
        run_frequency_refresh(runtime)

    @frequency_app.command("report")
    def report_command(
        limit: int = typer.Option(
            20,
            "--limit",
            "-n",
            help="Number of highest-frequency uncovered deck characters to show.",
        ),
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Print the full report as machine-readable JSON.",
        ),
    ) -> None:
        """Report reviewed-character coverage and highest-frequency gaps."""
        run_frequency_report(runtime, limit=limit, json_output=json_output)

    app.add_typer(frequency_app, name="frequency")
