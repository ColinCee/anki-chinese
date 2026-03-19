"""
CLI for generating and managing your Anki Chinese deck.

Commands:
    init            Parse source deck export + fill in pinyin, jyutping, examples
    audio           Generate pronunciation audio via Azure TTS
    build           Build the .apkg deck file (use --full for the complete pipeline)
    status          Show coverage stats and check for problems
    test-tts        Quick-test TTS for a single character or word
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from .config import (
    SOURCE_DECK_PATH,
    ENRICHED_PATH,
    GENERATED_MEDIA_DIR,
)
from .models import CharacterNote

app = typer.Typer(
    name="anki-chinese",
    help="Generate Anki decks for Chinese (Mandarin + Cantonese) using Heisig RSH.",
    no_args_is_help=True,
)
console = Console()


# ── init ──────────────────────────────────────────────────────────────


@app.command()
def init(
    input_file: Path = typer.Option(
        SOURCE_DECK_PATH,
        "--input",
        "-i",
        help="Anki text export to parse.",
    ),
    skip_examples: bool = typer.Option(
        False,
        "--skip-examples",
        help="Skip example-word lookup.",
    ),
):
    """Parse source deck export and enrich with pinyin, jyutping, examples."""
    from .pipeline.parser import parse_deck_export
    from .models import load_notes, save_notes
    from .pipeline.enrich import enrich_notes

    # Step 1: parse
    rprint(f"[blue]Parsing[/blue] {input_file} ...")
    notes = parse_deck_export(input_file)
    rprint(f"  [green]✓[/green] {len(notes)} notes parsed")

    # Step 2: preserve fields from previous enriched data that the fresh parse
    # may not have (audio filenames, mnemonics added directly in Anki, etc.)
    # This means you only need to re-export from Anki when you want to pull in
    # mnemonics you typed there; otherwise enriched.json is the source of truth.
    _PRESERVE_FIELDS = (
        "mandarin_audio",
        "cantonese_audio",
        "example_pinyin",
        "example_audio",
        "mnemonic",  # typed in Anki then exported once → kept forever after
    )
    if ENRICHED_PATH.exists():
        prev_notes = load_notes(ENRICHED_PATH)
        prev_by_hanzi = {n.hanzi: n for n in prev_notes}
        restored = 0
        for note in notes:
            prev = prev_by_hanzi.get(note.hanzi)
            if prev is None:
                continue
            for field in _PRESERVE_FIELDS:
                if not getattr(note, field) and getattr(prev, field):
                    setattr(note, field, getattr(prev, field))
                    restored += 1
        if restored:
            rprint(f"  [green]✓[/green] Restored {restored} fields from previous data")

    # Step 3: enrich
    rprint("[blue]Enriching[/blue] ...")
    notes = enrich_notes(notes, skip_examples=skip_examples)

    # Step 4: clear stale example audio when example_word changed
    from .pipeline.tts import example_audio_filename

    stale_files: list[Path] = []
    for note in notes:
        expected_audio = (
            f"[sound:{example_audio_filename(note.example_word, note.example_pinyin)}]"
            if note.example_word and note.example_pinyin
            else ""
        )
        if note.example_audio and note.example_audio != expected_audio:
            # Audio was for a different word — remove the reference
            # and clean up the orphaned file
            old_file = note.example_audio.replace("[sound:", "").rstrip("]")
            candidates = [GENERATED_MEDIA_DIR / old_file]
            stale_files.extend(p for p in candidates if p.exists())
            note.example_audio = ""

    if stale_files:
        removed = 0
        for p in stale_files:
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
        rprint(f"  [yellow]⚠[/yellow] Removed {removed} stale example audio files")

    _report_review_items(notes)

    save_notes(notes, ENRICHED_PATH)
    rprint(f"[green]✓[/green] Saved → {ENRICHED_PATH}")


# ── audio ─────────────────────────────────────────────────────────────


@app.command()
def audio(
    char: str = typer.Option(
        "",
        "--char",
        "-c",
        help="Generate audio for a single character only.",
    ),
    limit: int = typer.Option(
        0,
        "--limit",
        "-l",
        help="Process only the first N notes (0 = all).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Regenerate files that already exist.",
    ),
    fail_fast: bool = typer.Option(
        False,
        "--fail-fast",
        help="Stop immediately on first TTS error.",
    ),
):
    """Generate pronunciation audio via Azure TTS.

    Requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in .env.
    Skips files that already exist unless --force is set.
    """
    from .models import load_notes, save_notes
    from .pipeline.tts import (
        generate_mandarin,
        generate_cantonese,
        generate_example_audio,
    )

    all_notes = load_notes(ENRICHED_PATH)
    targets = all_notes

    if char:
        targets = [n for n in all_notes if n.hanzi == char]
        if not targets:
            rprint(f"[red]✗[/red] Character '{char}' not found")
            raise typer.Exit(1)
    elif limit > 0:
        targets = all_notes[:limit]

    rprint(f"[blue]Generating audio[/blue] for {len(targets)} notes ...")
    # Intentionally serial by default: Free (F0) TTS has low per-minute limits,
    # and bursty parallel requests are more likely to trigger 429 throttling.
    failures: list[str] = []

    for i, note in enumerate(targets, 1):
        rprint(f"  [{i}/{len(targets)}] {note.hanzi} ({note.keyword})")

        try:
            if note.pinyin:
                note.mandarin_audio = generate_mandarin(
                    note.hanzi,
                    note.pinyin,
                    force=force,
                )
            if note.jyutping:
                note.cantonese_audio = generate_cantonese(
                    note.hanzi,
                    note.jyutping,
                    force=force,
                )
            if note.example_word and note.example_pinyin:
                note.example_audio = generate_example_audio(
                    note.example_word,
                    note.example_pinyin,
                    force=force,
                )
        except Exception as e:
            failures.append(f"{note.hanzi} ({note.keyword}): {e}")
            rprint(f"    [red]✗[/red] {e}")
            if fail_fast:
                raise

    # Merge filtered results back into the full list
    if char or limit > 0:
        updated = {n.hanzi: n for n in targets}
        all_notes = [updated.get(n.hanzi, n) for n in all_notes]

    save_notes(all_notes, ENRICHED_PATH)
    rprint(f"[green]✓[/green] Audio done for {len(targets)} notes")
    if failures:
        rprint(
            f"[yellow]⚠ {len(failures)} notes failed during audio generation[/yellow]"
        )
        for failure in failures[:15]:
            rprint(f"  • {failure}")
        if len(failures) > 15:
            rprint(f"  … and {len(failures) - 15} more")


# ── build ─────────────────────────────────────────────────────────────


@app.command()
def build(
    full: bool = typer.Option(
        False,
        "--full",
        help="Run the complete pipeline: init → audio → build.",
    ),
    skip_audio: bool = typer.Option(
        False,
        "--skip-audio",
        help="When using --full, skip the audio step.",
    ),
    skip_examples: bool = typer.Option(
        False,
        "--skip-examples",
        help="When using --full, skip example-word lookup.",
    ),
    audio_limit: int = typer.Option(
        0,
        "--audio-limit",
        help="When using --full, limit audio generation to N notes.",
    ),
):
    """Build the .apkg deck from enriched data.

    Use --full to run the complete pipeline (init → audio → build)
    in a single command.
    """
    from .models import load_notes, save_notes
    from .pipeline.deck import build_deck

    if full:
        from .pipeline.parser import parse_deck_export
        from .pipeline.enrich import enrich_notes

        # 1. Init
        rprint("\n[bold]Step 1/3 · Parse + Enrich[/bold]")
        notes = parse_deck_export(SOURCE_DECK_PATH)
        notes = enrich_notes(notes, skip_examples=skip_examples)
        _report_review_items(notes)
        save_notes(notes, ENRICHED_PATH)

        # 2. Audio
        if not skip_audio:
            rprint("\n[bold]Step 2/3 · Audio[/bold]")
            from .pipeline.tts import (
                generate_mandarin,
                generate_cantonese,
                generate_example_audio,
            )

            targets = notes[:audio_limit] if audio_limit else notes
            failures: list[str] = []
            for note in targets:
                try:
                    if note.pinyin:
                        note.mandarin_audio = generate_mandarin(note.hanzi, note.pinyin)
                    if note.jyutping:
                        note.cantonese_audio = generate_cantonese(
                            note.hanzi, note.jyutping
                        )
                    if note.example_word and note.example_pinyin:
                        note.example_audio = generate_example_audio(
                            note.example_word,
                            note.example_pinyin,
                        )
                except Exception as e:
                    failures.append(f"{note.hanzi} ({note.keyword}): {e}")
            save_notes(notes, ENRICHED_PATH)
            rprint(f"  [green]✓[/green] Audio for {len(targets)} notes")
            if failures:
                rprint(
                    f"  [yellow]⚠ {len(failures)} notes failed during audio generation[/yellow]"
                )
        else:
            rprint("\n[bold]Step 2/3 · Audio[/bold] [dim](skipped)[/dim]")

        # 3. Build
        rprint("\n[bold]Step 3/3 · Build[/bold]")
        output_path = build_deck(notes)
        rprint(f"  [green]✓[/green] {output_path} ({len(notes)} notes)\n")
    else:
        notes = load_notes(ENRICHED_PATH)
        output_path = build_deck(notes)
        rprint(f"[green]✓[/green] Built {output_path} ({len(notes)} notes)")


# ── status ────────────────────────────────────────────────────────────


@app.command()
def status():
    """Show coverage stats and check for problems."""
    from .models import load_notes

    notes = load_notes(ENRICHED_PATH)

    # ── Coverage table ────────────────────────────────────────────
    table = Table(title=f"Coverage · {len(notes)} notes")
    table.add_column("Field", style="cyan")
    table.add_column("Filled", justify="right")
    table.add_column("Missing", justify="right")
    table.add_column("%", justify="right")

    for label, attr in [
        ("Hanzi", "hanzi"),
        ("Keyword", "keyword"),
        ("Pinyin", "pinyin"),
        ("Jyutping", "jyutping"),
        ("Mandarin Audio", "mandarin_audio"),
        ("Cantonese Audio", "cantonese_audio"),
        ("Example Word", "example_word"),
        ("Example Meaning", "example_meaning"),
        ("Example Pinyin", "example_pinyin"),
        ("Example Audio", "example_audio"),
        ("Stroke Order", "stroke_order"),
        ("Heisig №", "heisig_num"),
        ("Lesson", "lesson"),
        ("Mnemonic", "mnemonic"),
    ]:
        filled = sum(1 for n in notes if getattr(n, attr))
        missing = len(notes) - filled
        pct = filled / len(notes) * 100 if notes else 0
        color = "green" if pct > 90 else "yellow" if pct > 50 else "red"
        table.add_row(
            label, str(filled), str(missing), f"[{color}]{pct:.0f}%[/{color}]"
        )

    console.print(table)

    # ── Validation ────────────────────────────────────────────────
    issues: list[str] = []
    seen: dict[str, int] = {}

    for i, n in enumerate(notes):
        if n.hanzi in seen:
            issues.append(f"Duplicate '{n.hanzi}' at #{seen[n.hanzi]} and #{i}")
        seen[n.hanzi] = i

        if not n.hanzi:
            issues.append(f"#{i}: missing hanzi")
        if not n.keyword:
            issues.append(f"#{i} ({n.hanzi}): missing keyword")
        if not n.pinyin:
            issues.append(f"#{i} ({n.hanzi}): missing pinyin")
        if n.mandarin_audio and not n.pinyin:
            issues.append(f"#{i} ({n.hanzi}): audio without pinyin")
        if n.cantonese_audio and not n.jyutping:
            issues.append(f"#{i} ({n.hanzi}): audio without jyutping")
        if n.example_word and not n.example_pinyin:
            issues.append(f"#{i} ({n.hanzi}): example word without example pinyin")
        if n.example_audio and not n.example_pinyin:
            issues.append(f"#{i} ({n.hanzi}): example audio without example pinyin")

    review_count = sum(1 for n in notes if n.needs_review)

    if issues:
        rprint(f"\n[red]✗ {len(issues)} issues:[/red]")
        for issue in issues[:20]:
            rprint(f"  • {issue}")
        if len(issues) > 20:
            rprint(f"  … and {len(issues) - 20} more")
    else:
        rprint("\n[green]✓ No issues[/green]")

    if review_count:
        rprint(f"[yellow]⚠ {review_count} notes flagged for review[/yellow]")
        rprint("[dim]Run 'anki-chinese review' to inspect and verify them.[/dim]")


# ── review ────────────────────────────────────────────────────────────


@app.command()
def review():
    """Inspect notes flagged for review.

    \b
    Shows notes where the enrichment pipeline couldn't confidently
    pick the right data (e.g. polyphonic characters with no pinyin
    in the source).  Fix issues by adding entries to
    data/overrides.json, then re-run 'anki-chinese init'.
    """
    from .models import load_notes

    notes = load_notes(ENRICHED_PATH)
    flagged = [n for n in notes if n.needs_review]

    if not flagged:
        rprint("[green]✓ No notes need review.[/green]")
        return

    table = Table(
        title=f"Notes Needing Review · {len(flagged)} flagged",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Hanzi", style="bold", width=4)
    table.add_column("Pinyin", width=8)
    table.add_column("Keyword", width=18)
    table.add_column("Heisig", width=6)
    table.add_column("Reason", style="dim")

    for i, n in enumerate(flagged, 1):
        table.add_row(
            str(i),
            n.hanzi,
            n.pinyin,
            n.keyword,
            n.heisig_num,
            n.review_reason,
        )

    console.print(table)

    rprint(
        "\n[bold]To fix:[/bold] add corrections to [bold]data/overrides.json[/bold]:"
    )
    rprint('  [dim]{ "行": { "pinyin": "xíng" } }[/dim]')
    rprint("Then re-run [bold]anki-chinese init[/bold].\n")


# ── test-tts ──────────────────────────────────────────────────────────


@app.command(name="test-tts")
def test_tts(
    char: str = typer.Option(
        "",
        "--char",
        "-c",
        help="Character to test (looks up pinyin/jyutping from enriched data).",
    ),
    word: str = typer.Option(
        "",
        "--word",
        "-w",
        help="Arbitrary Mandarin text to synthesise (plain, no phoneme forcing).",
    ),
    voice: str = typer.Option(
        "",
        "--voice",
        "-v",
        help="Override Mandarin voice name (e.g. zh-CN-XiaoyiNeural) for comparison.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Regenerate even if the file already exists.",
    ),
):
    """Generate test audio for a single character or word.

    \b
    Examples:
      anki-chinese test-tts --char 电                           # default voice
      anki-chinese test-tts --char 电 --voice zh-CN-XiaoyiNeural  # compare voice
      anki-chinese test-tts --word 你好 --voice zh-CN-YunxiNeural

    Files are written into media/test/ with the voice short-name in the
    filename so you can A/B compare easily.
    """
    if not char and not word:
        rprint("[red]✗[/red] Pass --char or --word (or both).")
        raise typer.Exit(1)

    from .pipeline.tts import (
        _ssml_mandarin,
        _ssml_mandarin_text,
        _ssml_cantonese,
        _ssml_plain,
        _generate_audio,
    )
    from .config import MANDARIN_VOICE, TEST_MEDIA_DIR

    TEST_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Resolve voice: use override or default
    use_voice = voice or MANDARIN_VOICE
    # Short tag for filenames (e.g. "XiaoyiNeural" from "zh-CN-XiaoyiNeural")
    voice_tag = use_voice.split("-", 2)[-1] if "-" in use_voice else use_voice
    if voice:
        rprint(f"[dim]Voice:[/dim] {use_voice}")

    if char:
        # Try to look up the character in enriched data
        note: CharacterNote | None = None
        if ENRICHED_PATH.exists():
            from .models import load_notes

            all_notes = load_notes(ENRICHED_PATH)
            matches = [n for n in all_notes if n.hanzi == char]
            if matches:
                note = matches[0]

        if note:
            rprint(f"[blue]Testing[/blue] {note.hanzi} ({note.keyword})")

            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Type", style="cyan")
            table.add_column("File")
            table.add_column("Size", justify="right", style="dim")

            if note.pinyin:
                safe_pinyin = note.pinyin.replace(" ", "_")
                fname = f"{voice_tag}_cmn_{note.hanzi}_{safe_pinyin}.mp3"
                fpath = TEST_MEDIA_DIR / fname
                if not fpath.exists() or force:
                    ssml = _ssml_mandarin(note.hanzi, note.pinyin, voice=use_voice)
                    _generate_audio(ssml, fpath)
                size = fpath.stat().st_size if fpath.exists() else 0
                table.add_row(
                    "Mandarin",
                    fname,
                    f"{size:,} bytes",
                )

            if note.jyutping:
                safe_jp = note.jyutping.replace(" ", "_")
                fname = f"{voice_tag}_yue_{note.hanzi}_{safe_jp}.mp3"
                fpath = TEST_MEDIA_DIR / fname
                if not fpath.exists() or force:
                    ssml = _ssml_cantonese(note.hanzi, note.jyutping)
                    _generate_audio(ssml, fpath)
                size = fpath.stat().st_size if fpath.exists() else 0
                table.add_row(
                    "Cantonese",
                    fname,
                    f"{size:,} bytes",
                )

            if note.example_word:
                if note.example_pinyin:
                    safe_example_pinyin = note.example_pinyin.replace(" ", "_")
                    fname = (
                        f"{voice_tag}_cmn_{note.example_word}_{safe_example_pinyin}.mp3"
                    )
                    fpath = TEST_MEDIA_DIR / fname
                    if not fpath.exists() or force:
                        ssml = _ssml_mandarin_text(
                            note.example_word,
                            note.example_pinyin,
                            voice=use_voice,
                        )
                        _generate_audio(ssml, fpath)
                else:
                    fname = f"{voice_tag}_cmn_{note.example_word}.mp3"
                    fpath = TEST_MEDIA_DIR / fname
                    if not fpath.exists() or force:
                        ssml = _ssml_plain(
                            text=note.example_word,
                            voice=use_voice,
                            lang="zh-CN",
                        )
                        _generate_audio(ssml, fpath)
                size = fpath.stat().st_size if fpath.exists() else 0
                table.add_row(
                    f"Example ({note.example_word} · {note.example_pinyin or 'plain'})",
                    fname,
                    f"{size:,} bytes",
                )

            console.print(table)
        else:
            rprint(
                f"[yellow]⚠[/yellow] '{char}' not in enriched data — "
                "generating plain Mandarin audio only."
            )
            filename = f"{voice_tag}_test_{char}.mp3"
            output_path = TEST_MEDIA_DIR / filename
            ssml = _ssml_plain(text=char, voice=use_voice, lang="zh-CN")
            _generate_audio(ssml, output_path)
            rprint(f"  → {output_path} ({output_path.stat().st_size:,} bytes)")

    if word:
        rprint(f"[blue]Testing word[/blue] {word}")
        filename = f"{voice_tag}_test_{word}.mp3"
        output_path = TEST_MEDIA_DIR / filename

        if output_path.exists() and not force:
            rprint(f"  → {output_path} (cached, {output_path.stat().st_size:,} bytes)")
        else:
            ssml = _ssml_plain(text=word, voice=use_voice, lang="zh-CN")
            _generate_audio(ssml, output_path)
            rprint(f"  → {output_path} ({output_path.stat().st_size:,} bytes)")


# ── Helpers ───────────────────────────────────────────────────────────


def _report_review_items(notes: list[CharacterNote]) -> None:
    """Print a summary of notes that need manual review."""
    review = [n for n in notes if n.needs_review]
    if not review:
        return
    rprint(f"\n[yellow]⚠ {len(review)} notes need review:[/yellow]")
    for n in review[:15]:
        rprint(f"  {n.hanzi} ({n.keyword}): {n.review_reason}")
    if len(review) > 15:
        rprint(f"  … and {len(review) - 15} more")
    rprint("[dim]Run 'anki-chinese review' to see details and verify them.[/dim]")


if __name__ == "__main__":
    app()
