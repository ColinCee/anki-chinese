"""`anki-chinese songs` commands."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Protocol

import typer
from rich.table import Table

from ..activation import (
    ActivationResult,
    ActiveStateClient,
    AnkiClient,
    AnkiConnectClient,
    AnkiConnectError,
    ResuspendClient,
    ResuspendResult,
    resuspend_tagged_cards,
)
from ..config import ANKI_BACKUP_DIR
from ..songs import (
    LyricSong,
    SongActivationPlan,
    analyze_song_corpus,
    extract_cjk,
    fetch_lyrics_by_id,
    find_song,
    is_cjk,
    load_songs,
    plan_song_activation,
    save_lyrics,
    search_lyrics,
)
from .activate import run_activate_chars
from .app import AppRuntime


class KnowledgeClient(ActiveStateClient, Protocol):
    """Protocol for querying study state from live Anki."""


def _make_client() -> AnkiConnectClient:
    return AnkiConnectClient(api_key=os.getenv("ANKICONNECT_API_KEY", "").strip())


def _load_song_inputs(
    runtime: AppRuntime,
    *,
    lyrics_dir: Path,
    client: KnowledgeClient | None = None,
    include_studied: bool = False,
) -> tuple[list[LyricSong], set[str], set[str], set[str], list[str]]:
    """Load songs and live knowledge state from AnkiConnect."""
    songs = load_songs(lyrics_dir)
    ac: KnowledgeClient = client or _make_client()
    try:
        active_chars = ac.find_active_characters()
        studied_chars = ac.find_studied_characters() if include_studied else active_chars
        deck_order, deck_chars = ac.find_all_deck_info()
    except AnkiConnectError as error:
        runtime.console.print(f"[red]✗[/red] {error}")
        runtime.console.print(
            "[dim]Ensure Anki is open with AnkiConnect installed.[/dim]"
        )
        raise typer.Exit(2) from None
    return songs, active_chars, studied_chars, deck_chars, deck_order


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
    pace: int = 5,
    show_chars: bool = False,
    knowledge_client: KnowledgeClient | None = None,
) -> None:
    songs, active_chars, studied_chars, deck_chars, _deck_order = _load_song_inputs(
        runtime,
        lyrics_dir=lyrics_dir,
        client=knowledge_client,
        include_studied=True,
    )
    if not songs:
        runtime.console.print(f"[red]✗[/red] No lyric files found in {lyrics_dir}")
        raise typer.Exit(1)

    analysis = analyze_song_corpus(
        songs,
        active_chars=active_chars,
        learned_chars=studied_chars,
        deck_chars=deck_chars,
        pace=pace,
    )
    runtime.console.print(
        f"[bold]Deck:[/] {len(active_chars)} active · "
        f"{len(studied_chars)} studied · {len(deck_chars)} total characters\n"
    )

    table = Table(title="Progressive Sequence (greedy fewest-first)", title_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Song", style="cyan", no_wrap=True)
    table.add_column("Chars", justify="right")
    table.add_column("Known", justify="right")
    table.add_column("Learn", justify="right", style="yellow")
    table.add_column("Activate", justify="right", style="green")
    table.add_column("Unique", justify="right", style="magenta")
    table.add_column("Non-RSH", justify="right", style="dim")
    table.add_column("Cumul.", justify="right")
    table.add_column("Days", justify="right", style="green")
    for index, row in enumerate(analysis.sequence, 1):
        table.add_row(
            str(index),
            row.song.label,
            str(row.chars),
            f"{row.known} ({row.known_percent}%)",
            str(len(row.new_deck_chars)),
            str(len(row.activation_deck_chars)),
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
        str(sum(len(row.activation_deck_chars) for row in analysis.sequence)),
        "",
        "",
        str(analysis.sequence[-1].cumulative_deck_chars if analysis.sequence else 0),
        f"~{analysis.total_days}",
        style="bold",
    )
    runtime.console.print(table)

    if show_chars:
        for row in analysis.sequence:
            if row.new_deck_chars or row.activation_deck_chars:
                runtime.console.print(f"\n[cyan]{row.song.title}[/]")
                if row.new_deck_chars:
                    runtime.console.print(f"  Learn: {' '.join(row.new_deck_chars)}")
                if row.activation_deck_chars:
                    runtime.console.print(f"  Activate: {' '.join(row.activation_deck_chars)}")

    runtime.console.print(
        f"\n[bold]Summary[/bold] · {len(songs)} songs · "
        f"{len(analysis.new_deck_chars)} unstudied in-deck chars · "
        f"{len(analysis.non_deck_chars)} Non-RSH · ~{analysis.total_days} days"
    )


def _song_plan_from_query(
    runtime: AppRuntime,
    song_query: str,
    *,
    lyrics_dir: Path,
    limit: int,
    knowledge_client: KnowledgeClient | None = None,
) -> SongActivationPlan:
    songs, active_chars, _studied_chars, deck_chars, deck_order = _load_song_inputs(
        runtime,
        lyrics_dir=lyrics_dir,
        client=knowledge_client,
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


def _song_from_query(
    runtime: AppRuntime,
    song_query: str,
    *,
    lyrics_dir: Path,
) -> LyricSong:
    songs = load_songs(lyrics_dir)
    if not songs:
        runtime.console.print(f"[red]✗[/red] No lyric files found in {lyrics_dir}")
        raise typer.Exit(1)
    song = find_song(songs, song_query)
    if song is None:
        runtime.console.print(f"[red]✗[/red] Song not found or ambiguous: {song_query}")
        raise typer.Exit(1)
    return song


def _song_plan_from_next_sequence(
    runtime: AppRuntime,
    *,
    lyrics_dir: Path,
    limit: int,
    knowledge_client: KnowledgeClient | None = None,
) -> SongActivationPlan:
    songs, active_chars, _studied_chars, deck_chars, deck_order = _load_song_inputs(
        runtime,
        lyrics_dir=lyrics_dir,
        client=knowledge_client,
    )
    if not songs:
        runtime.console.print(f"[red]✗[/red] No lyric files found in {lyrics_dir}")
        raise typer.Exit(1)

    analysis = analyze_song_corpus(
        songs,
        active_chars=active_chars,
        deck_chars=deck_chars,
    )
    skipped_complete = 0
    selected_song: LyricSong | None = None
    for row in analysis.sequence:
        if row.new_deck_chars:
            selected_song = row.song
            break
        skipped_complete += 1

    if selected_song is None:
        runtime.console.print("[green]✓[/green] No songs have inactive in-deck chars")
        raise typer.Exit(0)

    if skipped_complete:
        runtime.console.print(
            f"[dim]Skipped {skipped_complete} songs with 0 inactive in-deck chars.[/dim]"
        )
    runtime.console.print(f"[dim]Auto-selected next song:[/dim] {selected_song.label}")
    return plan_song_activation(
        selected_song,
        active_chars=active_chars,
        deck_chars=deck_chars,
        deck_order=deck_order,
        limit=limit,
    )


def run_songs_next(
    runtime: AppRuntime,
    song_query: str = "",
    *,
    lyrics_dir: Path,
    limit: int = 20,
    knowledge_client: KnowledgeClient | None = None,
) -> SongActivationPlan:
    plan = (
        _song_plan_from_query(
            runtime,
            song_query,
            lyrics_dir=lyrics_dir,
            limit=limit,
            knowledge_client=knowledge_client,
        )
        if song_query
        else _song_plan_from_next_sequence(
            runtime,
            lyrics_dir=lyrics_dir,
            limit=limit,
            knowledge_client=knowledge_client,
        )
    )
    _print_song_plan(runtime, plan)
    return plan


def run_songs_activate(
    runtime: AppRuntime,
    song_query: str = "",
    *,
    lyrics_dir: Path,
    limit: int = 20,
    all_remaining: bool = False,
    dry_run: bool = False,
    tag: str = "",
    snapshot_dir: Path = ANKI_BACKUP_DIR,
    client: AnkiClient | None = None,
    knowledge_client: KnowledgeClient | None = None,
) -> ActivationResult | None:
    plan_limit = 0 if all_remaining else limit
    plan = run_songs_next(
        runtime,
        song_query,
        lyrics_dir=lyrics_dir,
        limit=plan_limit,
        knowledge_client=knowledge_client,
    )
    if not plan.chars:
        return
    activation_tag = tag or f"activated::song::{plan.song.title}"
    return run_activate_chars(
        runtime,
        list(plan.chars),
        dry_run=dry_run,
        tag=activation_tag,
        snapshot_dir=snapshot_dir,
        operation="activate-song",
        client=client,
    )


def _print_resuspend_result(
    runtime: AppRuntime,
    result: ResuspendResult,
    *,
    dry_run: bool,
    remove_tag: bool,
) -> None:
    preview = result.preview
    runtime.console.print(f"[bold]Tag:[/bold] {preview.tag}")
    runtime.console.print(f"[bold]Tagged notes:[/bold] {len(preview.note_ids)}")
    if preview.found_chars:
        runtime.console.print("  " + " ".join(preview.found_chars))

    if not preview.note_ids:
        runtime.console.print("[green]✓[/green] No tagged notes found")
        return

    if preview.cards_to_suspend:
        action = "Would resuspend" if dry_run else "Resuspended"
        runtime.console.print(
            f"[green]✓[/green] {action} {len(preview.cards_to_suspend)} cards "
            f"across {len(preview.note_ids_to_suspend)} notes"
        )
    else:
        runtime.console.print("[green]✓[/green] No active cards to resuspend")

    if preview.already_suspended_card_ids:
        runtime.console.print(
            f"[dim]Already suspended cards:[/dim] {len(preview.already_suspended_card_ids)}"
        )

    if remove_tag:
        tag_action = "Would remove" if dry_run else "Removed"
        runtime.console.print(
            f"  [dim]{tag_action} tag from {len(preview.note_ids)} notes[/dim]"
        )
    else:
        runtime.console.print("  [dim]Kept activation tag[/dim]")

    if result.snapshot_path is not None:
        runtime.console.print(f"  [dim]Undo snapshot:[/dim] {result.snapshot_path}")


def run_songs_resuspend(
    runtime: AppRuntime,
    song_query: str,
    *,
    lyrics_dir: Path,
    dry_run: bool = False,
    tag: str = "",
    keep_tag: bool = False,
    snapshot_dir: Path = ANKI_BACKUP_DIR,
    client: ResuspendClient | None = None,
) -> ResuspendResult:
    song = _song_from_query(runtime, song_query, lyrics_dir=lyrics_dir)
    activation_tag = tag or f"activated::song::{song.title}"
    ac: ResuspendClient = client or _make_client()
    try:
        result = resuspend_tagged_cards(
            ac,
            activation_tag,
            dry_run=dry_run,
            remove_tag=not keep_tag,
            snapshot_dir=snapshot_dir,
        )
    except AnkiConnectError as error:
        runtime.console.print(f"[red]✗[/red] {error}")
        runtime.console.print("[dim]Ensure Anki is open with AnkiConnect installed.[/dim]")
        raise typer.Exit(2) from None

    runtime.console.print(f"[bold]Song:[/bold] {song.label}")
    _print_resuspend_result(runtime, result, dry_run=dry_run, remove_tag=not keep_tag)
    return result


def run_songs_fetch(
    runtime: AppRuntime,
    query: str,
    *,
    lyrics_dir: Path,
    pick: int = 0,
    url: str = "",
) -> Path | None:
    """Search lyrics.net.cn and save lyrics as a markdown file."""
    if url:
        # Direct URL: extract ID from https://lyrics.net.cn/lyrics/<id>
        import re

        id_match = re.search(r"/lyrics/(\d+)", url)
        if not id_match:
            runtime.console.print(f"[red]✗[/red] Could not parse lyrics ID from URL: {url}")
            raise typer.Exit(1)
        lyric_id = int(id_match.group(1))
        runtime.console.print(f"[dim]Fetching lyrics from ID {lyric_id}...[/dim]")
        fetched = fetch_lyrics_by_id(lyric_id)
        path = save_lyrics(fetched, lyrics_dir)
        char_count = len(extract_cjk(fetched.lyrics))
        runtime.console.print(
            f"[green]✓[/green] Saved [cyan]{path.name}[/cyan] ({char_count} unique characters)"
        )
        return path

    # Search mode
    runtime.console.print(f"[dim]Searching lyrics.net.cn for: {query}[/dim]")
    results = search_lyrics(query)
    if not results:
        runtime.console.print(f"[red]✗[/red] No results found for: {query}")
        raise typer.Exit(1)

    if pick > 0:
        if pick > len(results):
            runtime.console.print(
                f"[red]✗[/red] Pick {pick} out of range (1-{len(results)})"
            )
            raise typer.Exit(1)
        selected = results[pick - 1]
    elif len(results) == 1:
        selected = results[0]
    else:
        # Show results and let user pick
        table = Table(title="Search Results", title_style="bold")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Title", style="cyan")
        table.add_column("Artist", style="green")
        table.add_column("URL", style="dim")
        for i, r in enumerate(results, 1):
            table.add_row(str(i), r.title, r.artist, r.url)
        runtime.console.print(table)
        runtime.console.print(
            "\n[yellow]Multiple results.[/yellow] Re-run with [bold]--pick N[/bold] "
            "or [bold]--url URL[/bold] to select one."
        )
        return None

    runtime.console.print(f"[dim]Fetching: {selected.label} (ID: {selected.id})[/dim]")
    fetched = fetch_lyrics_by_id(selected.id)
    path = save_lyrics(fetched, lyrics_dir)
    char_count = len(extract_cjk(fetched.lyrics))
    runtime.console.print(
        f"[green]✓[/green] Saved [cyan]{path.name}[/cyan] ({char_count} unique characters)"
    )
    return path


_TRADITIONAL_CHARS = (
    "個們來這時會說對為裡還過後從間開東點樣當經問機關長學動實現發"
    "見讓給頭愛報認話離進風夢裝卻歲歡買連輕雲傳飛聽遠廣親覺觀難"
    "記與寫總號體變萬歷華國議義無電農書節詞產獨滿燈腦嗎車線類識轉"
    "傷師邊條響媽塊數據導層構歡鐘離鏡驗戰廳環歸嘆議觸質達攝織職壓"
)


def run_songs_verify(runtime: AppRuntime, *, lyrics_dir: Path) -> bool:
    """Verify integrity of all lyric files. Returns True if all pass."""
    files = sorted(lyrics_dir.glob("*.md"))
    if not files:
        runtime.console.print(f"[red]✗[/red] No lyric files found in {lyrics_dir}")
        raise typer.Exit(1)

    errors: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []
    seen_titles: dict[str, str] = {}  # title -> filename (for duplicate detection)
    seen_artists_titles: dict[tuple[str, str], str] = {}  # (artist, title) -> filename

    # Expected numbering pattern
    number_re = re.compile(r"^(\d{2})-(.+)$")

    for i, path in enumerate(files):
        fname = path.stem
        num_match = number_re.match(fname)

        # Check numbering
        expected_num = f"{i + 1:02d}"
        if not num_match:
            errors.append((fname, "Missing number prefix (expected NN-artist-title)"))
        elif num_match.group(1) != expected_num:
            errors.append((fname, f"Number is {num_match.group(1)}, expected {expected_num}"))

        # Parse file
        try:
            from ..songs import parse_lyric_file

            song = parse_lyric_file(path)
        except ValueError as e:
            errors.append((fname, f"Parse error: {e}"))
            continue

        # Check frontmatter fields
        if not song.title:
            errors.append((fname, "Missing title in frontmatter"))
        if not song.artist:
            errors.append((fname, "Missing artist in frontmatter"))

        # Check filename matches frontmatter (ignoring punctuation)
        if num_match:
            clean_title = re.sub(r"[，。、！？·\s]", "", song.title)
            clean_artist = re.sub(r"[，。、！？·\s]", "", song.artist)
            expected_stem = f"{num_match.group(1)}-{clean_artist}-{clean_title}"
            actual_clean = re.sub(r"[，。、！？·\s]", "", fname)
            if actual_clean != expected_stem:
                warnings.append(
                    (fname, f"Filename doesn't match metadata (artist={song.artist}, title={song.title})")
                )

        # Check lyrics content
        if not song.lyrics.strip():
            errors.append((fname, "Empty lyrics"))
        elif len(song.lyrics.strip().split("\n")) < 4:
            warnings.append((fname, f"Very short lyrics ({len(song.lyrics.strip().split(chr(10)))} lines)"))

        # Check for stray HTML tags
        if re.search(r"<[a-z/]", song.lyrics):
            errors.append((fname, "Contains HTML tags in lyrics"))

        # Check for LRC timestamps like [00:15.30]
        if re.search(r"\[\d{2}:\d{2}", song.lyrics):
            errors.append((fname, "Contains LRC timestamps in lyrics"))

        # Check for traditional Chinese characters
        trad_found = {c for c in song.lyrics if c in _TRADITIONAL_CHARS}
        if trad_found:
            errors.append((fname, f"Traditional characters found: {' '.join(sorted(trad_found))}"))

        # Check title characters appear in lyrics
        title_cjk = {c for c in song.title if is_cjk(c)}
        lyrics_cjk = {c for c in song.lyrics if is_cjk(c)}
        missing_title_chars = title_cjk - lyrics_cjk
        if missing_title_chars:
            warnings.append(
                (fname, f"Title chars missing from lyrics: {' '.join(sorted(missing_title_chars))}")
            )

        # Check minimum unique character count
        char_count = len(extract_cjk(song.lyrics))
        if char_count < 20:
            warnings.append((fname, f"Very few unique characters ({char_count})"))

        # Check for duplicates by title
        if song.title in seen_titles:
            errors.append(
                (fname, f"Duplicate title '{song.title}' (also in {seen_titles[song.title]})")
            )
        seen_titles[song.title] = fname

        # Check for duplicates by artist+title
        key = (song.artist, song.title)
        if key in seen_artists_titles:
            errors.append(
                (fname, f"Duplicate song (also in {seen_artists_titles[key]})")
            )
        seen_artists_titles[key] = fname

    # Report
    if not errors and not warnings:
        runtime.console.print(
            f"[green]✓[/green] All {len(files)} lyric files pass verification."
        )
        return True

    if errors:
        table = Table(title="Errors", title_style="bold red")
        table.add_column("File", style="cyan")
        table.add_column("Issue", style="red")
        for fname, msg in errors:
            table.add_row(fname, msg)
        runtime.console.print(table)

    if warnings:
        table = Table(title="Warnings", title_style="bold yellow")
        table.add_column("File", style="cyan")
        table.add_column("Issue", style="yellow")
        for fname, msg in warnings:
            table.add_row(fname, msg)
        runtime.console.print(table)

    runtime.console.print(
        f"\n[bold]{len(files)} files:[/bold] "
        f"[red]{len(errors)} errors[/red] · [yellow]{len(warnings)} warnings[/yellow]"
    )
    return len(errors) == 0


def run_songs_verify_online(runtime: AppRuntime, *, lyrics_dir: Path) -> bool:
    """Verify lyrics against lyrics.net.cn. Returns True if all match."""
    import time

    files = sorted(lyrics_dir.glob("*.md"))
    if not files:
        runtime.console.print(f"[red]✗[/red] No lyric files found in {lyrics_dir}")
        raise typer.Exit(1)

    from ..songs import parse_lyric_file

    issues: list[tuple[str, str, str]] = []  # (filename, severity, message)
    skipped: list[str] = []

    for path in files:
        song = parse_lyric_file(path)
        runtime.console.print(f"[dim]Checking {song.label}...[/dim]", end=" ")

        try:
            results = search_lyrics(song.title)
        except Exception:
            runtime.console.print("[yellow]search failed[/yellow]")
            skipped.append(song.label)
            time.sleep(1)
            continue

        # Find best artist match
        match = None
        for r in results:
            if (
                r.artist == song.artist
                or song.artist in r.artist
                or r.artist in song.artist
            ):
                match = r
                break
        if not match:
            runtime.console.print("[yellow]not found[/yellow]")
            skipped.append(song.label)
            time.sleep(1)
            continue

        try:
            fetched = fetch_lyrics_by_id(match.id)
        except Exception:
            runtime.console.print("[yellow]fetch failed[/yellow]")
            skipped.append(song.label)
            time.sleep(1)
            continue

        # Compare CJK character sets (the meaningful comparison)
        local_cjk = {c for c in song.lyrics if is_cjk(c)}
        remote_cjk = {c for c in fetched.lyrics if is_cjk(c)}
        missing_chars = remote_cjk - local_cjk

        local_lines = len(song.lyrics.strip().split("\n"))
        remote_lines = len(fetched.lyrics.strip().split("\n"))
        line_diff = remote_lines - local_lines

        if not missing_chars and abs(line_diff) <= 5:
            runtime.console.print("[green]✓[/green]")
        elif missing_chars:
            missing_display = " ".join(sorted(missing_chars)[:15])
            severity = "error" if len(missing_chars) > 3 else "warning"
            msg = f"Missing {len(missing_chars)} chars from source: {missing_display}"
            if line_diff > 5:
                msg += f" (remote has {line_diff} more lines)"
            issues.append((path.stem, severity, msg))
            runtime.console.print(f"[red]✗ {msg}[/red]")
        elif line_diff > 5:
            msg = f"Local is {line_diff} lines shorter than source"
            issues.append((path.stem, "warning", msg))
            runtime.console.print(f"[yellow]⚠ {msg}[/yellow]")
        else:
            runtime.console.print("[green]✓[/green]")

        time.sleep(0.5)  # rate limit

    # Report
    runtime.console.print()
    if skipped:
        runtime.console.print(
            f"[dim]Skipped {len(skipped)}: {', '.join(skipped)}[/dim]\n"
        )

    if not issues:
        runtime.console.print(
            "[green]✓[/green] All checked songs match their online source."
        )
        return True

    error_count = sum(1 for _, sev, _ in issues if sev == "error")
    warn_count = sum(1 for _, sev, _ in issues if sev == "warning")
    table = Table(title="Online Verification Issues", title_style="bold")
    table.add_column("File", style="cyan")
    table.add_column("Issue")
    for fname, severity, msg in issues:
        style = "red" if severity == "error" else "yellow"
        table.add_row(fname, f"[{style}]{msg}[/{style}]")
    runtime.console.print(table)
    runtime.console.print(
        f"\n[bold]{len(files)} songs:[/bold] "
        f"[red]{error_count} errors[/red] · [yellow]{warn_count} warnings[/yellow] · "
        f"[dim]{len(skipped)} skipped[/dim]"
    )
    return error_count == 0


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
        pace: int = typer.Option(5, "--pace", min=1, help="Unstudied characters per day."),
        show_chars: bool = typer.Option(
            False,
            "--chars",
            help="Show unstudied character lists.",
        ),
    ) -> None:
        """Analyze song lyrics against the live Anki collection."""
        run_songs_analyze(
            runtime,
            lyrics_dir=lyrics_dir,
            pace=pace,
            show_chars=show_chars,
        )

    @songs_app.command("next")
    def next_command(
        song: str = typer.Argument(
            "",
            help=(
                "Song title, file stem, or unique substring. "
                "Omit to select the first song with inactive in-deck chars."
            ),
        ),
        limit: int = typer.Option(20, "--limit", "-n", min=0, help="Max chars to show."),
        lyrics_dir: Path = typer.Option(
            runtime.song_lyrics_dir,
            "--lyrics-dir",
            help="Directory of lyric markdown files.",
        ),
    ) -> None:
        """Show the next in-deck characters needed for a song."""
        run_songs_next(runtime, song, lyrics_dir=lyrics_dir, limit=limit)

    @songs_app.command("activate")
    def activate_command(
        song: str = typer.Argument(
            "",
            help=(
                "Song title, file stem, or unique substring. "
                "Omit to select the first song with inactive in-deck chars."
            ),
        ),
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
    ) -> None:
        """Unsuspend song cards after writing an undo snapshot."""
        run_songs_activate(
            runtime,
            song,
            lyrics_dir=lyrics_dir,
            limit=limit,
            all_remaining=all_remaining,
            dry_run=dry_run,
            tag=tag,
        )

    @songs_app.command("resuspend")
    def resuspend_command(
        song: str = typer.Argument(
            ...,
            help="Song title, file stem, or unique substring to reverse by activation tag.",
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Show tagged notes/cards without changing Anki.",
        ),
        tag: str = typer.Option("", "--tag", help="Override the activation tag to reverse."),
        keep_tag: bool = typer.Option(
            False,
            "--keep-tag",
            help="Suspend cards but leave the activation tag on notes.",
        ),
        lyrics_dir: Path = typer.Option(
            runtime.song_lyrics_dir,
            "--lyrics-dir",
            help="Directory of lyric markdown files.",
        ),
        snapshot_dir: Path = typer.Option(
            ANKI_BACKUP_DIR,
            "--snapshot-dir",
            help="Directory for live Anki undo snapshots.",
        ),
    ) -> None:
        """Resuspend cards from a mistaken song activation."""
        run_songs_resuspend(
            runtime,
            song,
            lyrics_dir=lyrics_dir,
            dry_run=dry_run,
            tag=tag,
            keep_tag=keep_tag,
            snapshot_dir=snapshot_dir,
        )

    @songs_app.command("fetch")
    def fetch_command(
        query: str = typer.Argument("", help="Song name to search for on lyrics.net.cn."),
        pick: int = typer.Option(0, "--pick", "-p", min=0, help="Pick the Nth result (1-based)."),
        url: str = typer.Option("", "--url", "-u", help="Direct lyrics.net.cn URL or ID."),
        lyrics_dir: Path = typer.Option(
            runtime.song_lyrics_dir,
            "--lyrics-dir",
            help="Directory to save lyric markdown files.",
        ),
    ) -> None:
        """Fetch song lyrics from lyrics.net.cn and save as markdown."""
        if not query and not url:
            runtime.console.print("[red]✗[/red] Provide a search query or --url.")
            raise typer.Exit(1)
        run_songs_fetch(runtime, query, lyrics_dir=lyrics_dir, pick=pick, url=url)

    @songs_app.command("verify")
    def verify_command(
        lyrics_dir: Path = typer.Option(
            runtime.song_lyrics_dir,
            "--lyrics-dir",
            help="Directory of lyric markdown files.",
        ),
        online: bool = typer.Option(
            False,
            "--online",
            help="Also verify lyrics against lyrics.net.cn (network required).",
        ),
    ) -> None:
        """Verify integrity of all lyric files (frontmatter, content, duplicates)."""
        ok = run_songs_verify(runtime, lyrics_dir=lyrics_dir)
        if online:
            online_ok = run_songs_verify_online(runtime, lyrics_dir=lyrics_dir)
            ok = ok and online_ok
        if not ok:
            raise typer.Exit(1)

    app.add_typer(songs_app, name="songs")
