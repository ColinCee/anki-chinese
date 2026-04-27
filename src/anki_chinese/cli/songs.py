"""`anki-chinese songs` commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from ..activation import AnkiClient
from ..songs import (
    LyricSong,
    SongActivationPlan,
    analyze_song_corpus,
    find_song,
    load_songs,
    plan_song_activation,
)
from .activate import run_activate_chars
from .app import AppRuntime


def _load_song_inputs(
    runtime: AppRuntime,
    *,
    lyrics_dir: Path,
    apkg_path: Path,
) -> tuple[list[LyricSong], set[str], set[str], list[str]]:
    songs = load_songs(lyrics_dir)
    active_chars = runtime.load_learned_hanzi(apkg_path)
    deck_order = [note.hanzi for note in runtime.parse_deck_export(apkg_path) if len(note.hanzi) == 1]
    deck_chars = set(deck_order) or runtime.load_deck_hanzi(apkg_path)
    return songs, active_chars, deck_chars, deck_order


def _print_song_plan(runtime: AppRuntime, plan: SongActivationPlan) -> None:
    runtime.console.print(f"[bold]Song:[/bold] {plan.song.label}")
    if plan.chars:
        runtime.console.print(f"[green]Next chars:[/green] {' '.join(plan.chars)}")
    else:
        runtime.console.print("[green]✓[/green] No remaining in-deck chars for this song")

    if plan.remaining_after_limit:
        runtime.console.print(
            f"[dim]{len(plan.remaining_after_limit)} more after limit:[/dim] "
            f"{' '.join(plan.remaining_after_limit)}"
        )
    if plan.non_deck_chars:
        runtime.console.print(
            f"[yellow]Non-RSH skipped:[/yellow] {' '.join(plan.non_deck_chars)}"
        )
    if plan.already_active:
        runtime.console.print(f"[dim]Already active:[/dim] {len(plan.already_active)}")


def run_songs_analyze(
    runtime: AppRuntime,
    *,
    lyrics_dir: Path,
    apkg_path: Path,
    pace: int = 5,
    show_chars: bool = False,
) -> None:
    songs, active_chars, deck_chars, _deck_order = _load_song_inputs(
        runtime,
        lyrics_dir=lyrics_dir,
        apkg_path=apkg_path,
    )
    if not songs:
        runtime.console.print(f"[red]✗[/red] No lyric files found in {lyrics_dir}")
        raise typer.Exit(1)

    analysis = analyze_song_corpus(
        songs,
        active_chars=active_chars,
        deck_chars=deck_chars,
        pace=pace,
    )
    runtime.console.print(
        f"[bold]Deck:[/] {len(active_chars)} active · {len(deck_chars)} total characters\n"
    )

    table = Table(title="Progressive Sequence (greedy fewest-first)", title_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Song", style="cyan", no_wrap=True)
    table.add_column("Chars", justify="right")
    table.add_column("Active", justify="right")
    table.add_column("New", justify="right", style="yellow")
    table.add_column("Unique", justify="right", style="magenta")
    table.add_column("Non-RSH", justify="right", style="dim")
    table.add_column("Cumul.", justify="right")
    table.add_column("Days", justify="right", style="green")
    for index, row in enumerate(analysis.sequence, 1):
        table.add_row(
            str(index),
            row.song.label,
            str(row.chars),
            f"{row.active} ({row.active_percent}%)",
            str(len(row.new_deck_chars)),
            str(row.unique_chars),
            str(len(row.non_deck_chars)) if row.non_deck_chars else "",
            str(row.cumulative_deck_chars),
            f"~{row.days}",
        )
    table.add_section()
    table.add_row(
        "",
        "TOTAL",
        "",
        "",
        str(sum(len(row.new_deck_chars) for row in analysis.sequence)),
        "",
        "",
        str(analysis.sequence[-1].cumulative_deck_chars if analysis.sequence else 0),
        f"~{analysis.total_days}",
        style="bold",
    )
    runtime.console.print(table)

    if show_chars:
        for row in analysis.sequence:
            if row.new_deck_chars:
                runtime.console.print(
                    f"\n[cyan]{row.song.title}[/]: {' '.join(row.new_deck_chars)}"
                )

    runtime.console.print(
        f"\n[bold]Summary[/bold] · {len(songs)} songs · "
        f"{len(analysis.new_deck_chars)} new in-deck chars · "
        f"{len(analysis.non_deck_chars)} Non-RSH · ~{analysis.total_days} days"
    )


def _song_plan_from_query(
    runtime: AppRuntime,
    song_query: str,
    *,
    lyrics_dir: Path,
    apkg_path: Path,
    limit: int,
) -> SongActivationPlan:
    songs, active_chars, deck_chars, deck_order = _load_song_inputs(
        runtime,
        lyrics_dir=lyrics_dir,
        apkg_path=apkg_path,
    )
    song = find_song(songs, song_query)
    if song is None:
        runtime.console.print(f"[red]✗[/red] Song not found or ambiguous: {song_query}")
        raise typer.Exit(1)
    return plan_song_activation(
        song,
        active_chars=active_chars,
        deck_chars=deck_chars,
        deck_order=deck_order,
        limit=limit,
    )


def run_songs_next(
    runtime: AppRuntime,
    song_query: str,
    *,
    lyrics_dir: Path,
    apkg_path: Path,
    limit: int = 20,
) -> SongActivationPlan:
    plan = _song_plan_from_query(
        runtime,
        song_query,
        lyrics_dir=lyrics_dir,
        apkg_path=apkg_path,
        limit=limit,
    )
    _print_song_plan(runtime, plan)
    return plan


def run_songs_activate(
    runtime: AppRuntime,
    song_query: str,
    *,
    lyrics_dir: Path,
    apkg_path: Path,
    limit: int = 20,
    all_remaining: bool = False,
    dry_run: bool = False,
    tag: str = "",
    client: AnkiClient | None = None,
) -> None:
    plan_limit = 0 if all_remaining else limit
    plan = run_songs_next(
        runtime,
        song_query,
        lyrics_dir=lyrics_dir,
        apkg_path=apkg_path,
        limit=plan_limit,
    )
    if not plan.chars:
        return
    activation_tag = tag or f"activated::song::{plan.song.title}"
    run_activate_chars(
        runtime,
        list(plan.chars),
        dry_run=dry_run,
        tag=activation_tag,
        client=client,
    )


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    songs_app = typer.Typer(
        name="songs",
        help="Analyze song lyrics and activate song character batches.",
        no_args_is_help=True,
    )

    @songs_app.command("analyze")
    def analyze_command(
        lyrics_dir: Path = typer.Option(
            runtime.song_lyrics_dir,
            "--lyrics-dir",
            help="Directory of lyric markdown files.",
        ),
        apkg_path: Path = typer.Option(
            runtime.source_deck_path,
            "--apkg",
            help="Exported .apkg snapshot to analyze.",
        ),
        pace: int = typer.Option(5, "--pace", min=1, help="New characters per day."),
        show_chars: bool = typer.Option(False, "--chars", help="Show new character lists."),
    ) -> None:
        """Analyze song lyrics against the exported deck snapshot."""
        run_songs_analyze(
            runtime,
            lyrics_dir=lyrics_dir,
            apkg_path=apkg_path,
            pace=pace,
            show_chars=show_chars,
        )

    @songs_app.command("next")
    def next_command(
        song: str = typer.Argument(..., help="Song title, file stem, or unique substring."),
        limit: int = typer.Option(20, "--limit", "-n", min=0, help="Max chars to show."),
        lyrics_dir: Path = typer.Option(
            runtime.song_lyrics_dir,
            "--lyrics-dir",
            help="Directory of lyric markdown files.",
        ),
        apkg_path: Path = typer.Option(
            runtime.source_deck_path,
            "--apkg",
            help="Exported .apkg snapshot to analyze.",
        ),
    ) -> None:
        """Show the next in-deck characters needed for a song."""
        run_songs_next(runtime, song, lyrics_dir=lyrics_dir, apkg_path=apkg_path, limit=limit)

    @songs_app.command("activate")
    def activate_command(
        song: str = typer.Argument(..., help="Song title, file stem, or unique substring."),
        limit: int = typer.Option(20, "--limit", "-n", min=1, help="Max chars to activate."),
        all_remaining: bool = typer.Option(
            False,
            "--all",
            help="Activate all remaining in-deck chars for this song.",
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Show matching notes/cards without changing Anki.",
        ),
        tag: str = typer.Option("", "--tag", help="Override the tag added to activated notes."),
        lyrics_dir: Path = typer.Option(
            runtime.song_lyrics_dir,
            "--lyrics-dir",
            help="Directory of lyric markdown files.",
        ),
        apkg_path: Path = typer.Option(
            runtime.source_deck_path,
            "--apkg",
            help="Exported .apkg snapshot used for song planning.",
        ),
    ) -> None:
        """Unsuspend the next live Anki cards needed for a song."""
        run_songs_activate(
            runtime,
            song,
            lyrics_dir=lyrics_dir,
            apkg_path=apkg_path,
            limit=limit,
            all_remaining=all_remaining,
            dry_run=dry_run,
            tag=tag,
        )

    app.add_typer(songs_app, name="songs")
