"""`anki-chinese card` commands for per-character overrides."""

from __future__ import annotations

from typing import Any

import typer
from rich.table import Table

from ..notes import CharacterNote, load_overrides, save_overrides
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
    if not runtime.note_store.exists():
        return None
    return next((note for note in runtime.note_store.load() if note.hanzi == hanzi), None)


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


def _print_override(runtime: AppRuntime, hanzi: str, override: dict[str, Any]) -> None:
    if not override:
        runtime.console.print(f"[dim]No manual override for {hanzi}.[/dim]")
        return

    table = Table(title=f"Override · {hanzi}")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    for field_name, value in override.items():
        table.add_row(field_name, str(value))
    runtime.console.print(table)


def run_card_show(runtime: AppRuntime, hanzi: str, *, json_output: bool = False) -> None:
    """Show saved note state and any manual override for a character."""

    key = hanzi.strip()
    if not key:
        runtime.console.print("[red]✗[/red] No character supplied")
        raise typer.Exit(1)

    note = _find_note(runtime, key)
    overrides = load_overrides(runtime.overrides_path)
    override = overrides.get(key, {})

    if json_output:
        runtime.console.print_json(
            data={
                "hanzi": key,
                "note": note.to_dict() if note is not None else None,
                "override": override,
            }
        )
        return

    _print_card(runtime, key, note)
    _print_override(runtime, key, override)


def _set_if_present(updates: dict[str, Any], field_name: str, value: str | None) -> None:
    if value is not None:
        updates[field_name] = value


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
    """Write manual overrides for a character."""

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
        runtime.console.print("[red]✗[/red] No override fields supplied")
        raise typer.Exit(1)

    unknown = sorted(set(updates) - _EDITABLE_FIELDS)
    if unknown:
        runtime.console.print(f"[red]✗[/red] Unsupported override fields: {', '.join(unknown)}")
        raise typer.Exit(1)

    if "sentence" in updates:
        updates["sentence_audio"] = ""

    overrides = load_overrides(runtime.overrides_path)
    current = dict(overrides.get(key, {}))
    current.update(updates)
    overrides[key] = current
    save_overrides(overrides, runtime.overrides_path)

    runtime.console.print(f"[green]✓[/green] Updated override for {key}")
    for field_name in updates:
        runtime.console.print(f"  {field_name}")
    runtime.console.print("[dim]Run `anki-chinese sync --dry-run` to preview required rebuild steps.[/dim]")
    return current


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    card_app = typer.Typer(
        name="card",
        help="Inspect and edit per-character manual overrides.",
        no_args_is_help=True,
    )

    @card_app.command("show")
    def show_command(
        hanzi: str = typer.Argument(..., help="Character to inspect."),
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Print the card and override as machine-readable JSON.",
        ),
    ) -> None:
        """Show saved note state and manual override."""

        run_card_show(runtime, hanzi, json_output=json_output)

    @card_app.command("set")
    def set_command(
        hanzi: str = typer.Argument(..., help="Character to edit."),
        meaning: str | None = typer.Option(None, "--meaning", help="Override meaning."),
        pinyin: str | None = typer.Option(None, "--pinyin", help="Override Mandarin pinyin."),
        jyutping: str | None = typer.Option(None, "--jyutping", help="Override Cantonese jyutping."),
        sentence: str | None = typer.Option(None, "--sentence", help="Override example sentence."),
        sentence_pinyin: str | None = typer.Option(
            None,
            "--sentence-pinyin",
            help="Override example sentence pinyin.",
        ),
        sentence_english: str | None = typer.Option(
            None,
            "--sentence-english",
            help="Override example sentence English.",
        ),
        story: str | None = typer.Option(None, "--story", help="Override mnemonic story."),
    ) -> None:
        """Set manual override fields for a character."""

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

    app.add_typer(card_app, name="card")
