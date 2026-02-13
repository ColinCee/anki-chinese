"""
CLI for generating and managing your Anki Chinese deck.

Commands:
    init     Parse old deck export + fill in pinyin, jyutping, examples
    audio    Generate pronunciation audio via Azure TTS
    build    Build the .apkg deck file (use --full for the complete pipeline)
    status   Show coverage stats and check for problems
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from .config import (
    OLD_DECK_PATH,
    ENRICHED_PATH,
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
        OLD_DECK_PATH,
        "--input",
        "-i",
        help="Old Anki text export to parse.",
    ),
    skip_examples: bool = typer.Option(
        False,
        "--skip-examples",
        help="Skip example-word lookup.",
    ),
):
    """Parse old deck export and enrich with pinyin, jyutping, examples."""
    from .parser import parse_old_deck
    from .models import save_notes
    from .enrich import enrich_notes

    # Step 1: parse
    rprint(f"[blue]Parsing[/blue] {input_file} ...")
    notes = parse_old_deck(input_file)
    rprint(f"  [green]✓[/green] {len(notes)} notes parsed")

    # Step 2: enrich
    rprint("[blue]Enriching[/blue] ...")
    notes = enrich_notes(notes, skip_examples=skip_examples)

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
):
    """Generate pronunciation audio via Azure TTS.

    Requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in .env.
    Skips files that already exist unless --force is set.
    """
    from .models import load_notes, save_notes
    from .tts import generate_mandarin, generate_cantonese, generate_example_audio

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

    for i, note in enumerate(targets, 1):
        rprint(f"  [{i}/{len(targets)}] {note.hanzi} ({note.keyword})")

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
        if note.example_word:
            note.example_audio = generate_example_audio(
                note.example_word,
                force=force,
            )

    # Merge filtered results back into the full list
    if char or limit > 0:
        updated = {n.hanzi: n for n in targets}
        all_notes = [updated.get(n.hanzi, n) for n in all_notes]

    save_notes(all_notes, ENRICHED_PATH)
    rprint(f"[green]✓[/green] Audio done for {len(targets)} notes")


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
    from .deck import build_deck

    if full:
        from .parser import parse_old_deck
        from .enrich import enrich_notes

        # 1. Init
        rprint("\n[bold]Step 1/3 · Parse + Enrich[/bold]")
        notes = parse_old_deck(OLD_DECK_PATH)
        notes = enrich_notes(notes, skip_examples=skip_examples)
        _report_review_items(notes)
        save_notes(notes, ENRICHED_PATH)

        # 2. Audio
        if not skip_audio:
            rprint("\n[bold]Step 2/3 · Audio[/bold]")
            from .tts import (
                generate_mandarin,
                generate_cantonese,
                generate_example_audio,
            )

            targets = notes[:audio_limit] if audio_limit else notes
            for note in targets:
                if note.pinyin:
                    note.mandarin_audio = generate_mandarin(note.hanzi, note.pinyin)
                if note.jyutping:
                    note.cantonese_audio = generate_cantonese(note.hanzi, note.jyutping)
                if note.example_word:
                    note.example_audio = generate_example_audio(note.example_word)
            save_notes(notes, ENRICHED_PATH)
            rprint(f"  [green]✓[/green] Audio for {len(targets)} notes")
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
