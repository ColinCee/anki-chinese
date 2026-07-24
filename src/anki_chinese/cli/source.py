"""`anki-chinese source` commands for canonical record maintenance."""

from __future__ import annotations

from pathlib import Path

import typer

from ..notes import migrate_notes_to_source
from .app import AppRuntime


def run_source_import(
    runtime: AppRuntime,
    input_file: Path,
    *,
    replace: bool = False,
    dry_run: bool = False,
) -> int:
    """Import a legacy APKG into canonical structured records."""

    if runtime.source_records_path is None:
        runtime.console.print("[red]✗[/red] Canonical source path is not configured")
        raise typer.Exit(1)
    if not input_file.is_file():
        runtime.console.print(f"[red]✗[/red] APKG not found: {input_file}")
        raise typer.Exit(1)
    if runtime.source_records_path.exists() and not replace:
        runtime.console.print(
            f"[red]✗[/red] Canonical source already exists: {runtime.source_records_path}. "
            "Use --replace to overwrite it."
        )
        raise typer.Exit(1)

    notes = runtime.parse_deck_export(input_file)
    custom_count = sum(note.curriculum.track == "custom" for note in notes)
    if dry_run:
        runtime.console.print(
            f"Would import {len(notes)} records ({custom_count} custom) "
            f"→ {runtime.source_records_path}"
        )
        return len(notes)

    try:
        migrate_notes_to_source(runtime.source_records_path, notes)
    except ValueError as error:
        runtime.console.print(f"[red]✗[/red] {error}")
        raise typer.Exit(1) from None
    runtime.console.print(
        f"[green]✓[/green] Imported {len(notes)} records ({custom_count} custom) "
        f"→ {runtime.source_records_path}"
    )
    runtime.console.print("[dim]Run `anki-chinese sync` to refresh generated state and the APKG.[/dim]")
    return len(notes)


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    source_app = typer.Typer(
        name="source",
        help="Maintain canonical structured character records.",
        no_args_is_help=True,
    )

    @source_app.command("import")
    def import_command(
        input_file: Path = typer.Option(
            runtime.source_deck_path,
            "--input",
            "-i",
            help="Legacy Anki .apkg export to import.",
        ),
        replace: bool = typer.Option(
            False,
            "--replace",
            help="Replace the existing canonical source.",
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Preview the import without changing source files.",
        ),
    ) -> None:
        """Import a legacy APKG into the canonical source."""

        run_source_import(runtime, input_file, replace=replace, dry_run=dry_run)

    app.add_typer(source_app, name="source")
