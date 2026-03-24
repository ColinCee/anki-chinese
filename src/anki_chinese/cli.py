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
import re

import typer
from rich import print as rprint
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
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


def _heisig_index(note: CharacterNote) -> int | None:
    match = re.search(r"\d+", note.heisig_num)
    return int(match.group(0)) if match else None


def _format_audio_task_labels(tasks: list[str]) -> str:
    labels = {
        "mandarin": "Mandarin",
        "cantonese": "Cantonese",
        "example": "Example",
    }
    return ", ".join(labels[task] for task in tasks if task in labels)


def _filter_from_rsh(notes: list[CharacterNote], start_rsh: int) -> list[CharacterNote]:
    return [note for note in notes if (_heisig_index(note) or 0) >= start_rsh]


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
    from .pipeline.tts import example_audio_filename, is_valid_audio_tag

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
    prev_by_hanzi: dict[str, CharacterNote] = {}
    if ENRICHED_PATH.exists():
        prev_notes = load_notes(ENRICHED_PATH)
        prev_by_hanzi = {n.hanzi: n for n in prev_notes}
        restored = 0
        for note in notes:
            prev = prev_by_hanzi.get(note.hanzi)
            if prev is None:
                continue
            for field in _PRESERVE_FIELDS:
                if field in {"example_pinyin", "example_audio"}:
                    if not note.example_word or note.example_word != prev.example_word:
                        continue
                prev_value = getattr(prev, field)
                if not getattr(note, field) and prev_value:
                    if field.endswith("_audio") and not is_valid_audio_tag(prev_value):
                        continue
                    setattr(note, field, prev_value)
                    restored += 1
        if restored:
            rprint(f"  [green]✓[/green] Restored {restored} fields from previous data")

    # Step 3: enrich
    rprint("[blue]Enriching[/blue] ...")
    notes = enrich_notes(notes, skip_examples=skip_examples)

    # Step 4: clear stale audio when pronunciation or example usage changed
    stale_files: list[Path] = []
    for note in notes:
        expected_mandarin_audio = (
            f"[sound:cmn_{note.hanzi}_{note.pinyin.replace(' ', '_')}.mp3]"
            if note.hanzi and note.pinyin
            else ""
        )
        if note.mandarin_audio and note.mandarin_audio != expected_mandarin_audio:
            old_file = note.mandarin_audio.replace("[sound:", "").rstrip("]")
            stale_files.extend(
                p for p in [GENERATED_MEDIA_DIR / old_file] if p.exists()
            )
            note.mandarin_audio = ""
        elif note.mandarin_audio and not is_valid_audio_tag(note.mandarin_audio):
            old_file = note.mandarin_audio.replace("[sound:", "").rstrip("]")
            stale_files.extend(
                p for p in [GENERATED_MEDIA_DIR / old_file] if p.exists()
            )
            note.mandarin_audio = ""

        expected_cantonese_audio = (
            f"[sound:yue_{note.hanzi}_{note.jyutping.replace(' ', '_')}.mp3]"
            if note.hanzi and note.jyutping
            else ""
        )
        if note.cantonese_audio and note.cantonese_audio != expected_cantonese_audio:
            old_file = note.cantonese_audio.replace("[sound:", "").rstrip("]")
            stale_files.extend(
                p for p in [GENERATED_MEDIA_DIR / old_file] if p.exists()
            )
            note.cantonese_audio = ""
        elif note.cantonese_audio and not is_valid_audio_tag(note.cantonese_audio):
            old_file = note.cantonese_audio.replace("[sound:", "").rstrip("]")
            stale_files.extend(
                p for p in [GENERATED_MEDIA_DIR / old_file] if p.exists()
            )
            note.cantonese_audio = ""

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
        elif note.example_audio and not is_valid_audio_tag(note.example_audio):
            old_file = note.example_audio.replace("[sound:", "").rstrip("]")
            candidates = [GENERATED_MEDIA_DIR / old_file]
            stale_files.extend(p for p in candidates if p.exists())
            note.example_audio = ""

    removed_stale_files = 0
    if stale_files:
        for p in stale_files:
            try:
                p.unlink()
                removed_stale_files += 1
            except OSError:
                pass
        rprint(
            f"  [yellow]⚠[/yellow] Removed {removed_stale_files} stale audio files"
        )

    _report_init_summary(
        notes=notes,
        prev_by_hanzi=prev_by_hanzi,
        restored_fields=restored if ENRICHED_PATH.exists() else 0,
        removed_stale_files=removed_stale_files,
    )
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
    start_rsh: int = typer.Option(
        0,
        "--start-rsh",
        help="Start audio generation from this Heisig/RSH number onward.",
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
        TTSRateLimitError,
        generate_mandarin,
        generate_cantonese,
        generate_example_audio,
        is_valid_audio_tag,
    )

    all_notes = load_notes(ENRICHED_PATH)
    targets = all_notes

    if char:
        targets = [n for n in all_notes if n.hanzi == char]
        if not targets:
            rprint(f"[red]✗[/red] Character '{char}' not found")
            raise typer.Exit(1)
    elif start_rsh > 0:
        targets = _filter_from_rsh(all_notes, start_rsh)
        if not targets:
            rprint(f"[red]✗[/red] No notes found at or after RSH #{start_rsh}")
            raise typer.Exit(1)
        if limit > 0:
            targets = targets[:limit]
    elif limit > 0:
        targets = all_notes[:limit]

    pending: list[tuple[CharacterNote, list[str]]] = []
    for note in targets:
        tasks = _audio_tasks_for_note(note, force=force, is_valid_audio_tag=is_valid_audio_tag)
        if tasks:
            pending.append((note, tasks))

    if not pending:
        rprint(f"[green]✓[/green] Audio already up to date for {len(targets)} notes")
        return

    skipped = len(targets) - len(pending)
    rprint(f"[blue]Audio[/blue] {len(pending)} notes need updates")
    if skipped:
        rprint(f"  [dim]{skipped} notes already had valid audio[/dim]")

    # Intentionally serial by default: Free (F0) TTS has low per-minute limits,
    # and bursty parallel requests are more likely to trigger 429 throttling.
    failures: list[str] = []
    repaired = {"mandarin": 0, "cantonese": 0, "example": 0}
    synced = {"mandarin": 0, "cantonese": 0, "example": 0}
    changed_chars: list[str] = []

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TextColumn("[dim]{task.fields[current]}[/dim]"),
        console=console,
    )

    with progress:
        task_id = progress.add_task(
            "Audio",
            total=len(pending),
            current="Preparing...",
        )

        for i, (note, tasks) in enumerate(pending, 1):
            note_changed = False
            progress.update(
                task_id,
                current=(
                    f"{note.hanzi} ({note.keyword}) · {_format_audio_task_labels(tasks)}"
                ),
            )

            try:
                if "mandarin" in tasks and note.pinyin:
                    expected = _expected_mandarin_audio_tag(note)
                    had_valid_audio = bool(expected and is_valid_audio_tag(expected))
                    note.mandarin_audio = generate_mandarin(
                        note.hanzi,
                        note.pinyin,
                        force=force,
                    )
                    repaired["mandarin"] += 0 if had_valid_audio and not force else 1
                    synced["mandarin"] += 1 if had_valid_audio and not force else 0
                    note_changed = True
                if "cantonese" in tasks and note.jyutping:
                    expected = _expected_cantonese_audio_tag(note)
                    had_valid_audio = bool(expected and is_valid_audio_tag(expected))
                    note.cantonese_audio = generate_cantonese(
                        note.hanzi,
                        note.jyutping,
                        force=force,
                    )
                    repaired["cantonese"] += 0 if had_valid_audio and not force else 1
                    synced["cantonese"] += 1 if had_valid_audio and not force else 0
                    note_changed = True
                if "example" in tasks and note.example_word and note.example_pinyin:
                    expected = _expected_example_audio_tag(note)
                    had_valid_audio = bool(expected and is_valid_audio_tag(expected))
                    note.example_audio = generate_example_audio(
                        note.example_word,
                        note.example_pinyin,
                        force=force,
                    )
                    repaired["example"] += 0 if had_valid_audio and not force else 1
                    synced["example"] += 1 if had_valid_audio and not force else 0
                    note_changed = True
                if note_changed:
                    changed_chars.append(note.hanzi)
                progress.advance(task_id)
            except TTSRateLimitError as e:
                progress.stop()
                failures.append(f"{note.hanzi} ({note.keyword}): {e}")
                rprint(f"[yellow]⚠[/yellow] {e}")
                if char or limit > 0 or start_rsh > 0:
                    updated = {n.hanzi: n for n in targets}
                    all_notes = [updated.get(n.hanzi, n) for n in all_notes]
                save_notes(all_notes, ENRICHED_PATH)
                _report_audio_summary(
                    processed=i - 1,
                    total=len(pending),
                    repaired=repaired,
                    synced=synced,
                    changed_chars=changed_chars,
                )
                rprint(
                    f"[yellow]Stopped on Azure rate limit at {note.hanzi} (RSH #{_heisig_index(note) or '?' }). Re-run the same audio command later.[/yellow]"
                )
                raise typer.Exit(2)
            except Exception as e:
                failures.append(f"{note.hanzi} ({note.keyword}): {e}")
                rprint(f"[red]✗[/red] {note.hanzi} ({note.keyword}): {e}")
                progress.advance(task_id)
                if fail_fast:
                    raise

    # Merge filtered results back into the full list
    if char or limit > 0 or start_rsh > 0:
        updated = {n.hanzi: n for n in targets}
        all_notes = [updated.get(n.hanzi, n) for n in all_notes]

    save_notes(all_notes, ENRICHED_PATH)
    _report_audio_summary(
        processed=len(pending),
        total=len(pending),
        repaired=repaired,
        synced=synced,
        changed_chars=changed_chars,
    )
    rprint(f"[green]✓[/green] Audio done")
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
    audio_start_rsh: int = typer.Option(
        0,
        "--audio-start-rsh",
        help="When using --full, start audio generation from this Heisig/RSH number.",
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
                TTSRateLimitError,
                generate_mandarin,
                generate_cantonese,
                generate_example_audio,
            )

            targets = (
                _filter_from_rsh(notes, audio_start_rsh) if audio_start_rsh else notes
            )
            if audio_start_rsh and not targets:
                rprint(
                    f"  [red]✗[/red] No notes found at or after RSH #{audio_start_rsh}"
                )
                raise typer.Exit(1)
            if audio_limit:
                targets = targets[:audio_limit]
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
                except TTSRateLimitError as e:
                    failures.append(f"{note.hanzi} ({note.keyword}): {e}")
                    save_notes(notes, ENRICHED_PATH)
                    rprint(f"  [yellow]⚠[/yellow] {e}")
                    rprint(
                        "  [yellow]Stopped on Azure rate limit. Re-run audio later, then build.[/yellow]"
                    )
                    raise typer.Exit(2)
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


def _expected_mandarin_audio_tag(note: CharacterNote) -> str:
    if not note.hanzi or not note.pinyin:
        return ""
    return f"[sound:cmn_{note.hanzi}_{note.pinyin.replace(' ', '_')}.mp3]"


def _expected_cantonese_audio_tag(note: CharacterNote) -> str:
    if not note.hanzi or not note.jyutping:
        return ""
    return f"[sound:yue_{note.hanzi}_{note.jyutping.replace(' ', '_')}.mp3]"


def _expected_example_audio_tag(note: CharacterNote) -> str:
    if not note.example_word or not note.example_pinyin:
        return ""
    safe_pinyin = note.example_pinyin.replace(" ", "_")
    return f"[sound:cmn_{note.example_word}_{safe_pinyin}.mp3]"


def _audio_tasks_for_note(note: CharacterNote, *, force: bool, is_valid_audio_tag) -> list[str]:  # type: ignore[no-untyped-def]
    tasks: list[str] = []
    mandarin_tag = _expected_mandarin_audio_tag(note)
    if mandarin_tag and (force or note.mandarin_audio != mandarin_tag or not is_valid_audio_tag(mandarin_tag)):
        tasks.append("mandarin")

    cantonese_tag = _expected_cantonese_audio_tag(note)
    if cantonese_tag and (force or note.cantonese_audio != cantonese_tag or not is_valid_audio_tag(cantonese_tag)):
        tasks.append("cantonese")

    example_tag = _expected_example_audio_tag(note)
    if example_tag and (force or note.example_audio != example_tag or not is_valid_audio_tag(example_tag)):
        tasks.append("example")

    return tasks


def _report_init_summary(
    *,
    notes: list[CharacterNote],
    prev_by_hanzi: dict[str, CharacterNote],
    restored_fields: int,
    removed_stale_files: int,
) -> None:
    prev_hanzi = set(prev_by_hanzi)
    added = [note.hanzi for note in notes if note.hanzi not in prev_hanzi]
    removed = sorted(prev_hanzi - {note.hanzi for note in notes})
    changed_existing = 0
    tracked_fields = (
        "keyword",
        "pinyin",
        "jyutping",
        "example_word",
        "example_meaning",
        "example_pinyin",
        "mandarin_audio",
        "cantonese_audio",
        "example_audio",
        "mnemonic",
    )
    for note in notes:
        prev = prev_by_hanzi.get(note.hanzi)
        if prev and any(getattr(note, field) != getattr(prev, field) for field in tracked_fields):
            changed_existing += 1

    rprint("\n[bold]Init Summary[/bold]")
    rprint(f"  [green]•[/green] {len(notes)} notes ready")
    if added:
        preview = ", ".join(added[:12])
        suffix = "" if len(added) <= 12 else f" … +{len(added) - 12} more"
        rprint(f"  [green]•[/green] {len(added)} new characters: {preview}{suffix}")
    if changed_existing:
        rprint(f"  [green]•[/green] {changed_existing} existing characters updated")
    if removed:
        preview = ", ".join(removed[:12])
        suffix = "" if len(removed) <= 12 else f" … +{len(removed) - 12} more"
        rprint(f"  [yellow]•[/yellow] {len(removed)} characters removed: {preview}{suffix}")
    if restored_fields:
        rprint(f"  [green]•[/green] {restored_fields} cached fields reused")
    if removed_stale_files:
        rprint(f"  [yellow]•[/yellow] {removed_stale_files} stale audio files removed")


def _report_audio_summary(
    *,
    processed: int,
    total: int,
    repaired: dict[str, int],
    synced: dict[str, int],
    changed_chars: list[str],
) -> None:
    repaired_total = sum(repaired.values())
    synced_total = sum(synced.values())
    rprint("\n[bold]Audio Summary[/bold]")
    rprint(f"  [green]•[/green] {processed}/{total} notes processed")
    if repaired_total or synced_total:
        if repaired_total:
            rprint(f"  [green]•[/green] {repaired_total} new audio files generated")
        if synced_total:
            rprint(f"  [green]•[/green] {synced_total} existing audio files linked to notes")

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Audio Type")
        table.add_column("Generated", justify="right")
        table.add_column("Linked Existing", justify="right")
        table.add_row("Mandarin", str(repaired["mandarin"]), str(synced["mandarin"]))
        table.add_row("Cantonese", str(repaired["cantonese"]), str(synced["cantonese"]))
        table.add_row("Example", str(repaired["example"]), str(synced["example"]))
        console.print(table)
    if changed_chars:
        preview = ", ".join(changed_chars[:12])
        suffix = "" if len(changed_chars) <= 12 else f" … +{len(changed_chars) - 12} more"
        rprint(f"  [green]•[/green] Updated characters: {preview}{suffix}")


if __name__ == "__main__":
    app()
