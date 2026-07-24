"""`anki-chinese card` commands for per-character source-deck edits."""

from __future__ import annotations

from typing import Any

import typer
from rich.table import Table

from ..notes import CharacterNote
from ..notes.model import Curriculum
from ..notes.source import (
    CharacterSourceStore,
    add_source_record,
    is_single_hanzi,
    migrate_notes_to_source,
    update_source_record,
    validate_track,
)
from .app import AppRuntime

_EDITABLE_FIELDS = {
    "meaning",
    "pinyin",
    "jyutping",
    "sentence",
    "sentence_pinyin",
    "sentence_english",
    "story",
}


def _find_note(runtime: AppRuntime, hanzi: str) -> CharacterNote | None:
    if runtime.note_store.exists():
        note = next((note for note in runtime.note_store.load() if note.hanzi == hanzi), None)
        if note is not None:
            return note
    if runtime.source_records_path is not None and runtime.source_records_path.exists():
        return next(
            (
                note
                for note in CharacterSourceStore(runtime.source_records_path).load()
                if note.hanzi == hanzi
            ),
            None,
        )
    return None


def _print_card(runtime: AppRuntime, hanzi: str, note: CharacterNote | None) -> None:
    if note is None:
        runtime.console.print(f"[yellow]⚠[/yellow] {hanzi} is not in saved enriched state.")
        return

    table = Table(title=f"Card · {hanzi}")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    for field_name in [
        "meaning",
        "pinyin",
        "jyutping",
        "sentence",
        "sentence_pinyin",
        "sentence_english",
        "sentence_audio",
        "story",
    ]:
        table.add_row(field_name, str(getattr(note, field_name)))
    runtime.console.print(table)


def run_card_show(runtime: AppRuntime, hanzi: str, *, json_output: bool = False) -> None:
    """Show saved note state for a character."""

    key = hanzi.strip()
    if not key:
        runtime.console.print("[red]✗[/red] No character supplied")
        raise typer.Exit(1)

    note = _find_note(runtime, key)

    if json_output:
        runtime.console.print_json(
            data={
                "hanzi": key,
                "note": note.to_dict() if note is not None else None,
            }
        )
        return

    _print_card(runtime, key, note)


def _set_if_present(updates: dict[str, Any], field_name: str, value: str | None) -> None:
    if value is not None:
        updates[field_name] = value


def _refresh_cached_note(runtime: AppRuntime, hanzi: str, updates: dict[str, Any]) -> None:
    if not runtime.note_store.exists():
        return
    notes = runtime.note_store.load()
    note = next((candidate for candidate in notes if candidate.hanzi == hanzi), None)
    if note is None:
        return
    for field_name, value in updates.items():
        setattr(note, field_name, value)
    runtime.note_store.save(notes)


def run_card_set(
    runtime: AppRuntime,
    hanzi: str,
    *,
    meaning: str | None = None,
    pinyin: str | None = None,
    jyutping: str | None = None,
    sentence: str | None = None,
    sentence_pinyin: str | None = None,
    sentence_english: str | None = None,
    story: str | None = None,
) -> dict[str, Any]:
    """Write source-deck fields for a character."""

    key = hanzi.strip()
    if not key:
        runtime.console.print("[red]✗[/red] No character supplied")
        raise typer.Exit(1)

    updates: dict[str, Any] = {}
    _set_if_present(updates, "meaning", meaning)
    _set_if_present(updates, "pinyin", pinyin)
    _set_if_present(updates, "jyutping", jyutping)
    _set_if_present(updates, "sentence", sentence)
    _set_if_present(updates, "sentence_pinyin", sentence_pinyin)
    _set_if_present(updates, "sentence_english", sentence_english)
    _set_if_present(updates, "story", story)

    if not updates:
        runtime.console.print("[red]✗[/red] No edit fields supplied")
        raise typer.Exit(1)

    sentence_fields = {"sentence", "sentence_pinyin", "sentence_english"}
    changed_sentence_fields = sentence_fields.intersection(updates)
    if changed_sentence_fields and changed_sentence_fields != sentence_fields:
        runtime.console.print(
            "[red]✗[/red] --sentence, --sentence-pinyin, and --sentence-english "
            "must be supplied together"
        )
        raise typer.Exit(1)

    unknown = sorted(set(updates) - _EDITABLE_FIELDS)
    if unknown:
        runtime.console.print(f"[red]✗[/red] Unsupported edit fields: {', '.join(unknown)}")
        raise typer.Exit(1)

    if "sentence" in updates:
        updates["sentence_audio"] = ""

    try:
        if runtime.source_records_path is not None and runtime.source_records_path.exists():
            update_source_record(runtime.source_records_path, key, updates)
        else:
            runtime.update_source_note(runtime.source_deck_path, key, updates)
    except FileNotFoundError:
        runtime.console.print(f"[red]✗[/red] Source deck not found: {runtime.source_deck_path}")
        raise typer.Exit(1) from None
    except KeyError:
        runtime.console.print(f"[red]✗[/red] {key} is not in source deck: {runtime.source_deck_path}")
        raise typer.Exit(1) from None
    except ValueError as error:
        runtime.console.print(f"[red]✗[/red] {error}")
        raise typer.Exit(1) from None

    _refresh_cached_note(runtime, key, updates)

    runtime.console.print(f"[green]✓[/green] Updated source deck for {key}")
    for field_name in updates:
        runtime.console.print(f"  {field_name}")
    runtime.console.print("[dim]Run `anki-chinese sync --dry-run` to preview required rebuild steps.[/dim]")
    return dict(updates)


def run_card_add(
    runtime: AppRuntime,
    hanzi: str,
    *,
    meaning: str | None = None,
    pinyin: str | None = None,
    jyutping: str | None = None,
    sentence: str | None = None,
    sentence_pinyin: str | None = None,
    sentence_english: str | None = None,
    story: str | None = None,
    stroke_order: str | None = None,
    track: str = "custom",
    rsh_number: int | None = None,
    lesson: str = "",
    origin: str = "manual",
    collection: str = "",
) -> CharacterNote:
    """Add one new character to the canonical source records."""

    key = hanzi.strip()
    if not is_single_hanzi(key):
        runtime.console.print("[red]✗[/red] Add exactly one Chinese character")
        raise typer.Exit(1)
    if not meaning or not meaning.strip():
        runtime.console.print("[red]✗[/red] --meaning is required")
        raise typer.Exit(1)
    sentence_values = [sentence, sentence_pinyin, sentence_english]
    if any(value is not None for value in sentence_values) and not all(sentence_values):
        runtime.console.print(
            "[red]✗[/red] --sentence, --sentence-pinyin, and --sentence-english must be supplied together"
        )
        raise typer.Exit(1)
    try:
        normalized_track = validate_track(track)
    except ValueError as error:
        runtime.console.print(f"[red]✗[/red] {error}")
        raise typer.Exit(1) from None
    if normalized_track == "rsh" and rsh_number is None:
        runtime.console.print("[red]✗[/red] --rsh-number is required for --track rsh")
        raise typer.Exit(1)
    if normalized_track == "custom" and rsh_number is not None:
        runtime.console.print("[red]✗[/red] Custom records cannot have --rsh-number")
        raise typer.Exit(1)

    if runtime.source_records_path is None:
        runtime.console.print(
            "[red]✗[/red] Canonical source path is not configured for this runtime"
        )
        raise typer.Exit(1)

    source_store = CharacterSourceStore(runtime.source_records_path)
    if not source_store.exists():
        try:
            migrate_notes_to_source(
                runtime.source_records_path,
                runtime.parse_deck_export(runtime.source_deck_path),
            )
        except FileNotFoundError:
            runtime.console.print(
                f"[red]✗[/red] Legacy source deck not found: {runtime.source_deck_path}"
            )
            raise typer.Exit(1) from None
        except ValueError as error:
            runtime.console.print(f"[red]✗[/red] {error}")
            raise typer.Exit(1) from None

    curriculum = Curriculum(
        track=normalized_track,
        rsh_number=rsh_number,
        lesson=lesson.strip(),
        origin=origin.strip(),
        collection=collection.strip(),
    )
    note = CharacterNote(
        hanzi=key,
        meaning=meaning.strip(),
        pinyin=(pinyin or "").strip(),
        jyutping=(jyutping or "").strip(),
        sentence=(sentence or "").strip(),
        sentence_pinyin=(sentence_pinyin or "").strip(),
        sentence_english=(sentence_english or "").strip(),
        story=(story or "").strip(),
        stroke_order=(stroke_order or f'<img src="{ord(key):x}.gif" />').strip(),
        heisig_num=str(rsh_number or ""),
        lesson=lesson.strip(),
        curriculum=curriculum,
    )
    try:
        add_source_record(runtime.source_records_path, note)
    except (KeyError, ValueError) as error:
        runtime.console.print(f"[red]✗[/red] {error}")
        raise typer.Exit(1) from None

    runtime.console.print(f"[green]✓[/green] Added canonical source record for {key}")
    runtime.console.print(f"  curriculum: {normalized_track}")
    runtime.console.print(
        "[dim]Run `anki-chinese sync --dry-run` to preview enrichment, audio, and build.[/dim]"
    )
    return note


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    card_app = typer.Typer(
        name="card",
        help="Inspect and edit per-character source-deck fields.",
        no_args_is_help=True,
    )

    @card_app.command("show")
    def show_command(
        hanzi: str = typer.Argument(..., help="Character to inspect."),
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Print the card as machine-readable JSON.",
        ),
    ) -> None:
        """Show saved note state."""

        run_card_show(runtime, hanzi, json_output=json_output)

    @card_app.command("set")
    def set_command(
        hanzi: str = typer.Argument(..., help="Character to edit."),
        meaning: str | None = typer.Option(
            None,
            "--meaning",
            help="Set a compact, sense-aware meaning and relevant compound usage.",
        ),
        pinyin: str | None = typer.Option(None, "--pinyin", help="Set Mandarin pinyin."),
        jyutping: str | None = typer.Option(None, "--jyutping", help="Set Cantonese jyutping."),
        sentence: str | None = typer.Option(None, "--sentence", help="Set example sentence."),
        sentence_pinyin: str | None = typer.Option(
            None,
            "--sentence-pinyin",
            help="Set example sentence pinyin.",
        ),
        sentence_english: str | None = typer.Option(
            None,
            "--sentence-english",
            help="Set example sentence English.",
        ),
        story: str | None = typer.Option(None, "--story", help="Set mnemonic story."),
    ) -> None:
        """Set source-deck fields for a character."""

        run_card_set(
            runtime,
            hanzi,
            meaning=meaning,
            pinyin=pinyin,
            jyutping=jyutping,
            sentence=sentence,
            sentence_pinyin=sentence_pinyin,
            sentence_english=sentence_english,
            story=story,
        )

    @card_app.command("add")
    def add_command(
        hanzi: str = typer.Argument(..., help="One character to add."),
        meaning: str | None = typer.Option(
            None,
            "--meaning",
            help="Sense-aware gloss; include relevant compound usage.",
        ),
        pinyin: str | None = typer.Option(None, "--pinyin", help="Set Mandarin pinyin."),
        jyutping: str | None = typer.Option(None, "--jyutping", help="Set Cantonese jyutping."),
        sentence: str | None = typer.Option(None, "--sentence", help="Set an example sentence."),
        sentence_pinyin: str | None = typer.Option(
            None,
            "--sentence-pinyin",
            help="Set example sentence pinyin.",
        ),
        sentence_english: str | None = typer.Option(
            None,
            "--sentence-english",
            help="Set example sentence English.",
        ),
        story: str | None = typer.Option(None, "--story", help="Set mnemonic story."),
        stroke_order: str | None = typer.Option(
            None,
            "--stroke-order",
            help="Override the default Unicode stroke-order image reference.",
        ),
        track: str = typer.Option(
            "custom",
            "--track",
            help="Curriculum track: custom or rsh.",
        ),
        rsh_number: int | None = typer.Option(
            None,
            "--rsh-number",
            help="Actual RSH number when --track rsh is used.",
        ),
        lesson: str = typer.Option("", "--lesson", help="Optional curriculum lesson."),
        origin: str = typer.Option("manual", "--origin", help="Record origin."),
        collection: str = typer.Option("", "--collection", help="Optional study collection."),
    ) -> None:
        """Add a character to canonical source records."""

        run_card_add(
            runtime,
            hanzi,
            meaning=meaning,
            pinyin=pinyin,
            jyutping=jyutping,
            sentence=sentence,
            sentence_pinyin=sentence_pinyin,
            sentence_english=sentence_english,
            story=story,
            stroke_order=stroke_order,
            track=track,
            rsh_number=rsh_number,
            lesson=lesson,
            origin=origin,
            collection=collection,
        )

    app.add_typer(card_app, name="card")
