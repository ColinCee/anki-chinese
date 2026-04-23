#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "opencc-python-reimplemented",
#     "requests",
#     "rich",
#     "zstandard",
# ]
# ///
"""Analyze song lyrics against the Anki deck to calculate new characters needed.

Reads the current Anki deck export to determine known characters, then analyzes
song lyric files to show how many new characters each song requires.

Usage:
    uv run python scripts/analyze_songs.py
    uv run python scripts/analyze_songs.py --sequence 01-小潘潘-学猫叫,02-邓丽君-月亮代表我的心
    uv run python scripts/analyze_songs.py --pace 6
    uv run python scripts/analyze_songs.py --chars  # show new character lists
    uv run python scripts/analyze_songs.py fetch "孤勇者" "陈奕迅"  # fetch lyrics from LRCLIB
"""

from __future__ import annotations

import argparse
import io
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import requests
import zstandard
from opencc import OpenCC
from rich.console import Console
from rich.table import Table

console = Console()

LYRICS_DIR = Path(__file__).parent / "lyrics"
APKG_PATH = Path(__file__).parent.parent / "data" / "source" / "All Decks.apkg"
LRCLIB_SEARCH_URL = "https://lrclib.net/api/search"


def is_cjk(char: str) -> bool:
    cp = ord(char)
    return (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF)


def extract_cjk(text: str) -> set[str]:
    return {c for c in text if is_cjk(c)}


def load_deck_characters(apkg_path: Path) -> tuple[set[str], set[str]]:
    """Returns (known_chars, all_deck_chars) from the apkg export."""
    with zipfile.ZipFile(apkg_path, "r") as z:
        raw = z.read("collection.anki21b")

    dctx = zstandard.ZstdDecompressor()
    reader = dctx.stream_reader(io.BytesIO(raw))
    db_bytes = reader.read()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(db_bytes)
        db_path = Path(f.name)

    try:
        conn = sqlite3.connect(str(db_path))
        conn.create_collation(
            "unicase", lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower())
        )

        # Known = any unsuspended card for the note (matches apkg_reader.py logic)
        rows = conn.execute(
            """
            SELECT DISTINCT n.flds FROM cards c JOIN notes n ON c.nid = n.id
            WHERE c.queue != -1
            """
        ).fetchall()
        known = set()
        for (flds,) in rows:
            char = flds.split("\x1f")[0]
            if len(char) == 1 and is_cjk(char):
                known.add(char)

        # All characters in the deck
        all_rows = conn.execute("SELECT flds FROM notes").fetchall()
        deck_chars = set()
        for (flds,) in all_rows:
            char = flds.split("\x1f")[0]
            if len(char) == 1 and is_cjk(char):
                deck_chars.add(char)

        conn.close()
    finally:
        db_path.unlink(missing_ok=True)

    return known, deck_chars


def parse_lyric_file(path: Path) -> dict:
    """Parse a .md lyric file with YAML frontmatter."""
    text = path.read_text(encoding="utf-8")

    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"No frontmatter found in {path}")

    frontmatter, lyrics = match.groups()
    metadata: dict = {}
    for line in frontmatter.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    metadata["lyrics"] = lyrics.strip()
    metadata["characters"] = extract_cjk(lyrics)
    metadata["file"] = path.stem
    return metadata


def fetch_lyrics(
    song_name: str,
    artist: str,
    lyrics_dir: Path,
    *,
    list_only: bool = False,
    pick: int | None = None,
) -> Path | None:
    """Search LRCLIB for lyrics and save as simplified Chinese .md file."""
    cc = OpenCC("t2s")
    params: dict[str, str] = {"track_name": song_name}
    if artist:
        params["artist_name"] = artist
    print(f"Searching LRCLIB for: {song_name}" + (f" by {artist}" if artist else ""))

    resp = requests.get(LRCLIB_SEARCH_URL, params=params, timeout=10)
    resp.raise_for_status()
    results = resp.json()

    # Retry without artist filter if no results (handles romanized artist names)
    if not results and artist:
        print(f"  No results with artist filter, retrying track name only...")
        resp = requests.get(
            LRCLIB_SEARCH_URL, params={"track_name": song_name}, timeout=10
        )
        resp.raise_for_status()
        results = resp.json()

    # Fallback to free-text search (handles punctuation in titles)
    if not results:
        query = f"{song_name} {artist}" if artist else song_name
        print(f"  No exact match, trying free-text search...")
        resp = requests.get(
            LRCLIB_SEARCH_URL, params={"q": query}, timeout=10
        )
        resp.raise_for_status()
        results = resp.json()

    if not results:
        print("  ✗ No results found")
        return None

    # Filter to results that actually have plain lyrics
    results = [r for r in results if r.get("plainLyrics")]

    if not results:
        print("  ✗ Results found but none have lyrics")
        return None

    if list_only:
        for i, r in enumerate(results, 1):
            dur = f"{int(r['duration'] // 60)}:{int(r['duration'] % 60):02d}" if r.get("duration") else "?"
            print(f"  {i:>2}. {r['trackName']} - {r['artistName']} [{dur}] (ID: {r['id']})")
        return None

    if pick is not None:
        if pick < 1 or pick > len(results):
            print(f"  ✗ Pick must be between 1 and {len(results)}")
            return None
        selected = results[pick - 1]
    else:
        selected = results[0]

    matched_name = selected["trackName"]
    matched_artist = selected["artistName"]
    album = selected.get("albumName", "")
    print(f"  Found: {matched_name} - {matched_artist}" + (f" [{album}]" if album else ""))

    plain = selected["plainLyrics"]
    lyrics_text = cc.convert(plain)

    # Strip common credit headers some submitters include in plainLyrics
    cleaned_lines = []
    for line in lyrics_text.split("\n"):
        stripped = line.strip()
        # Skip lines like "词：方文山", "曲：周杰伦", "编曲：黄雨勋"
        if re.match(r"^(词|曲|编曲|作词|作曲|制作人?|演唱)\s*[：:]", stripped):
            continue
        # Skip standalone title lines that match the song name
        if stripped and stripped == cc.convert(matched_name):
            continue
        # Skip "title(extra info)" lines at the very start
        if not cleaned_lines and stripped and cc.convert(song_name) in stripped and len(stripped) < 50:
            continue
        cleaned_lines.append(line)

    # Trim leading/trailing blank lines
    while cleaned_lines and not cleaned_lines[0].strip():
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()

    lyrics_text = "\n".join(cleaned_lines)

    # Use the requested song/artist names for the file (cleaner than API names)
    file_artist = cc.convert(artist) if artist else cc.convert(matched_artist)
    file_title = cc.convert(song_name)

    filename = f"{file_artist}-{file_title}.md"
    filepath = lyrics_dir / filename
    content = f"---\ntitle: {file_title}\nartist: {file_artist}\n---\n{lyrics_text}\n"

    filepath.write_text(content, encoding="utf-8")
    print(f"  ✓ Saved to {filepath.relative_to(filepath.parent.parent.parent)}")

    char_count = len(extract_cjk(lyrics_text))
    print(f"  {char_count} unique Chinese characters")
    return filepath


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze song lyrics against Anki deck"
    )
    subparsers = parser.add_subparsers(dest="command")

    # fetch subcommand
    fetch_parser = subparsers.add_parser("fetch", help="Fetch lyrics from LRCLIB")
    fetch_parser.add_argument("song", help="Song name in Chinese")
    fetch_parser.add_argument("artist", nargs="?", default="", help="Artist name")
    fetch_parser.add_argument(
        "--lyrics-dir", type=Path, default=LYRICS_DIR, help="Output directory"
    )
    fetch_parser.add_argument(
        "--pick", type=int, metavar="N", help="Pick the Nth result (1-based) instead of auto-match"
    )
    fetch_parser.add_argument(
        "--list", action="store_true", help="List search results without downloading"
    )

    # analyze (default) - all flags go on the main parser
    parser.add_argument(
        "--apkg", type=Path, default=APKG_PATH, help="Path to .apkg file"
    )
    parser.add_argument(
        "--lyrics-dir", type=Path, default=LYRICS_DIR, help="Lyric .md directory"
    )
    parser.add_argument(
        "--sequence",
        type=str,
        help="Comma-separated song filenames (without .md) in desired order",
    )
    parser.add_argument(
        "--pace", type=int, default=5, metavar="N",
        help="New characters per day (default: 5, min: 1)"
    )
    parser.add_argument(
        "--chars", action="store_true", help="Show new character lists for each song"
    )
    args = parser.parse_args()

    if hasattr(args, "pace") and args.pace < 1:
        parser.error("--pace must be at least 1")

    if args.command == "fetch":
        lyrics_dir = args.lyrics_dir
        lyrics_dir.mkdir(parents=True, exist_ok=True)
        try:
            fetch_lyrics(
                args.song,
                args.artist,
                lyrics_dir,
                list_only=args.list,
                pick=args.pick,
            )
        except requests.RequestException as e:
            print(f"  ✗ Network error: {e}")
            raise SystemExit(1)
        return

    analyze(args)


def analyze(args: argparse.Namespace) -> None:
    """Run the analysis against the Anki deck."""
    known, deck_chars = load_deck_characters(args.apkg)
    console.print(
        f"[bold]Deck:[/] {len(known)} known · {len(deck_chars)} total characters\n"
    )

    songs = []
    for path in sorted(args.lyrics_dir.glob("*.md")):
        songs.append(parse_lyric_file(path))

    if not songs:
        console.print(f"[red]No lyric files found in {args.lyrics_dir}[/]")
        return

    # ── Character frequency across songs (for unique-to-song stats) ──
    from collections import Counter

    char_song_freq: Counter[str] = Counter()
    for song in songs:
        for c in song["characters"]:
            char_song_freq[c] += 1

    # ── Progressive sequence ──
    if args.sequence:
        sequence_names = [s.strip() for s in args.sequence.split(",")]
        song_by_file = {s["file"]: s for s in songs}
        sequence = []
        for name in sequence_names:
            if name in song_by_file:
                sequence.append(song_by_file[name])
            else:
                console.print(f"[yellow]⚠ '{name}' not found, skipping[/]")
    else:
        remaining = list(songs)
        sequence = []
        cumulative = set(known)
        while remaining:
            remaining.sort(
                key=lambda s: len((s["characters"] - cumulative) & deck_chars)
            )
            best = remaining.pop(0)
            sequence.append(best)
            cumulative |= (best["characters"] - cumulative) & deck_chars

    mode = "specified" if args.sequence else "greedy fewest-first"
    seq_table = Table(title=f"Progressive Sequence ({mode})", title_style="bold")
    seq_table.add_column("#", justify="right", style="dim")
    seq_table.add_column("Song", style="cyan", no_wrap=True)
    seq_table.add_column("Chars", justify="right")
    seq_table.add_column("Known", justify="right")
    seq_table.add_column("New", justify="right", style="yellow")
    seq_table.add_column("Unique", justify="right", style="magenta")
    seq_table.add_column("Non-RSH", justify="right", style="dim")
    seq_table.add_column("Cumul.", justify="right")
    seq_table.add_column("Days", justify="right", style="green")

    cumulative = set(known)
    total_new = 0
    total_days = 0
    total_non_rsh = 0

    for i, song in enumerate(sequence, 1):
        chars = song["characters"]
        new = (chars - cumulative) & deck_chars
        non_rsh = chars - deck_chars - known
        unique = sum(1 for c in chars if char_song_freq[c] == 1)
        known_ct = len(chars & cumulative)
        pct = round(known_ct / len(chars) * 100) if chars else 0
        cumulative |= new
        total_new += len(new)
        total_non_rsh += len(non_rsh)
        days = len(new) // args.pace + (1 if len(new) % args.pace else 0)
        total_days += days

        title = song.get("title", song["file"])
        artist = song.get("artist", "")
        label = f"{title} ({artist})" if artist else title
        seq_table.add_row(
            str(i),
            label,
            str(len(chars)),
            f"{known_ct} ({pct}%)",
            str(len(new)),
            str(unique),
            str(len(non_rsh)) if non_rsh else "",
            str(len(cumulative)),
            f"~{days}",
        )

    seq_table.add_section()
    seq_table.add_row(
        "", "TOTAL", "", "", str(total_new), "", "",
        str(len(cumulative)), f"~{total_days}", style="bold",
    )

    console.print()
    console.print(seq_table)

    if args.chars:
        cumulative_chars = set(known)
        for song in sequence:
            chars = song["characters"]
            new = (chars - cumulative_chars) & deck_chars
            cumulative_chars |= new
            if new:
                title = song.get("title", song["file"])
                console.print(f"\n[cyan]{title}[/]: {' '.join(sorted(new))}")

    # ── Characters not in deck ──
    all_song_chars: set[str] = set()
    for song in songs:
        all_song_chars |= song["characters"]
    all_not_in_deck = all_song_chars - deck_chars

    if all_not_in_deck:
        nd_table = Table(title="Characters Not in Deck", title_style="bold")
        nd_table.add_column("Song", style="cyan", no_wrap=True)
        nd_table.add_column("Count", justify="right", style="red")
        nd_table.add_column("Characters", style="dim")

        for song in sequence:
            chars = song["characters"]
            missing = chars - deck_chars
            if missing:
                title = song.get("title", song["file"])
                artist = song.get("artist", "")
                label = f"{title} ({artist})" if artist else title
                nd_table.add_row(label, str(len(missing)), " ".join(sorted(missing)))

        nd_table.add_section()
        nd_table.add_row("TOTAL (unique)", str(len(all_not_in_deck)), " ".join(sorted(all_not_in_deck)), style="bold")

        console.print()
        console.print(nd_table)

    # ── Summary stats ──
    all_new_in_deck = (all_song_chars - known) & deck_chars
    coverage_before = len(known) / len(deck_chars) * 100
    coverage_after = len(cumulative) / len(deck_chars) * 100

    # Character overlap: how many chars appear in 2+ songs
    shared = sum(1 for c, n in char_song_freq.items() if n >= 2)
    avg_overlap = sum(char_song_freq.values()) / len(char_song_freq) if char_song_freq else 0

    # Hardest/easiest songs by unique chars (chars that only appear in that one song)
    unique_per_song: list[tuple[str, int]] = []
    for song in songs:
        title = song.get("title", song["file"])
        unique_to_song = sum(1 for c in (song["characters"] - known) & deck_chars if char_song_freq[c] == 1)
        unique_per_song.append((title, unique_to_song))
    unique_per_song.sort(key=lambda x: -x[1])

    stats_table = Table(title="Summary", title_style="bold")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", justify="right")

    stats_table.add_row("Songs", str(len(songs)))
    stats_table.add_row("Unique chars across all songs", str(len(all_song_chars)))
    stats_table.add_row("New chars to learn (in deck)", str(len(all_new_in_deck)))
    stats_table.add_row("Not in deck (learn from context)", str(len(all_not_in_deck)))
    stats_table.add_row("Deck coverage before", f"{coverage_before:.1f}%")
    stats_table.add_row("Deck coverage after", f"{coverage_after:.1f}%")
    stats_table.add_section()
    stats_table.add_row("Chars appearing in 2+ songs", str(shared))
    stats_table.add_row("Avg songs per char", f"{avg_overlap:.1f}")
    stats_table.add_section()
    stats_table.add_row("Most unique new chars", f"{unique_per_song[0][0]} ({unique_per_song[0][1]})")
    stats_table.add_row("Fewest unique new chars", f"{unique_per_song[-1][0]} ({unique_per_song[-1][1]})")
    stats_table.add_section()
    stats_table.add_row(f"Est. time @ {args.pace}/day", f"~{total_days} days ({total_days / 7:.0f} weeks)")

    console.print()
    console.print(stats_table)
    console.print()


if __name__ == "__main__":
    main()
