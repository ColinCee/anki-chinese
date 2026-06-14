"""`anki-chinese activate` commands for live Anki unsuspension."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from ..activation import (
    ActivationPreview,
    ActivationResult,
    AnkiClient,
    AnkiConnectClient,
    AnkiConnectError,
    activate_characters,
    normalize_character_args,
)
from ..config import ANKI_BACKUP_DIR
from .app import AppRuntime
from .interaction import preview_unless_confirmed


def _default_client() -> AnkiConnectClient:
    return AnkiConnectClient(api_key=os.getenv("ANKICONNECT_API_KEY", "").strip())


def _print_preview(
    runtime: AppRuntime,
    preview: ActivationPreview,
    *,
    dry_run: bool,
    tag: str,
) -> None:
    runtime.console.print(f"[bold]Requested[/bold] {len(preview.requested_chars)} chars")
    if preview.requested_chars:
        runtime.console.print("  " + " ".join(preview.requested_chars))

    if preview.missing_chars:
        runtime.console.print(
            f"[yellow]⚠[/yellow] Missing from live Anki: {' '.join(preview.missing_chars)}"
        )
    if preview.already_active_chars:
        runtime.console.print(
            f"[dim]Already active:[/dim] {' '.join(preview.already_active_chars)}"
        )

    if not preview.suspended_card_ids:
        runtime.console.print("[green]✓[/green] No suspended cards to activate")
        return

    action = "Would activate" if dry_run else "Activated"
    runtime.console.print(
        f"[green]✓[/green] {action} {len(preview.suspended_card_ids)} cards "
        f"across {len(preview.note_ids)} notes"
    )
    if tag:
        tag_action = "Would tag" if dry_run else "Tagged"
        runtime.console.print(f"  [dim]{tag_action} notes with:[/dim] {tag}")


def _print_result(
    runtime: AppRuntime,
    result: ActivationResult,
    *,
    dry_run: bool,
    tag: str,
) -> None:
    _print_preview(runtime, result.preview, dry_run=dry_run, tag=tag)
    if result.snapshot_path is not None:
        runtime.console.print(f"  [dim]Undo snapshot:[/dim] {result.snapshot_path}")


def run_activate_chars(
    runtime: AppRuntime,
    chars: list[str],
    *,
    dry_run: bool = False,
    tag: str = "",
    client: AnkiClient | None = None,
    snapshot_dir: Path = ANKI_BACKUP_DIR,
    operation: str = "activate-chars",
) -> ActivationResult:
    normalized = normalize_character_args(chars)
    if not normalized:
        runtime.console.print("[red]✗[/red] No Chinese characters supplied")
        raise typer.Exit(1)

    client = client or _default_client()
    try:
        result = activate_characters(
            client,
            normalized,
            tag=tag,
            dry_run=dry_run,
            snapshot_dir=snapshot_dir,
            operation=operation,
        )
    except AnkiConnectError as error:
        runtime.console.print(f"[red]✗[/red] {error}")
        raise typer.Exit(2) from None

    _print_result(runtime, result, dry_run=dry_run, tag=tag)
    return result


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    activate_app = typer.Typer(
        name="activate",
        help="Unsuspend existing cards in the live Anki collection with undo snapshots.",
        no_args_is_help=True,
    )

    @activate_app.command("chars")
    def chars_command(
        chars: list[str] = typer.Argument(..., help="Characters to activate."),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Show matching notes/cards without changing Anki.",
        ),
        tag: str = typer.Option(
            "",
            "--tag",
            help="Optional tag to add to notes that are activated.",
        ),
        confirm: bool = typer.Option(
            False,
            "--confirm",
            help="Mutate live Anki after writing an undo snapshot. Without this, only previews.",
        ),
    ) -> None:
        """Unsuspend specific characters by Hanzi."""
        effective_dry_run = preview_unless_confirmed(
            runtime.console,
            dry_run=dry_run,
            confirm=confirm,
            action="Activating cards",
        )
        run_activate_chars(runtime, chars, dry_run=effective_dry_run, tag=tag)

    app.add_typer(activate_app, name="activate")
