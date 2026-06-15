"""`anki-chinese activate` commands for live Anki unsuspension."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.table import Table

from ..activation import (
    ActivationPreview,
    ActivationResult,
    AnkiClient,
    AnkiConnectClient,
    AnkiConnectError,
    SnapshotError,
    activate_characters,
    list_activation_snapshots,
    load_activation_snapshot,
    normalize_character_args,
    resolve_activation_snapshot,
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


def _snapshot_chars_text(chars: list[str]) -> str:
    if not chars:
        return ""
    text = " ".join(chars[:12])
    if len(chars) > 12:
        text += f" … +{len(chars) - 12}"
    return text


def run_snapshot_list(
    runtime: AppRuntime,
    *,
    snapshot_dir: Path = ANKI_BACKUP_DIR,
    limit: int = 20,
    json_output: bool = False,
) -> None:
    snapshots = list_activation_snapshots(snapshot_dir, limit=limit)
    if json_output:
        runtime.console.print_json(data=[snapshot.summary_dict() for snapshot in snapshots])
        return

    if not snapshots:
        runtime.console.print(f"[yellow]No activation snapshots found in {snapshot_dir}[/yellow]")
        return

    table = Table(title=f"Activation snapshots · {snapshot_dir}")
    table.add_column("Created")
    table.add_column("Operation")
    table.add_column("Chars", justify="right")
    table.add_column("Notes", justify="right")
    table.add_column("Cards", justify="right")
    table.add_column("Tag")
    table.add_column("File")
    for snapshot in snapshots:
        table.add_row(
            snapshot.created_at,
            snapshot.operation,
            str(len(snapshot.found_chars)),
            str(snapshot.note_count),
            str(snapshot.mutation_card_count),
            snapshot.tag,
            snapshot.path.name,
        )
    runtime.console.print(table)


def run_snapshot_show(
    runtime: AppRuntime,
    reference: str,
    *,
    snapshot_dir: Path = ANKI_BACKUP_DIR,
    json_output: bool = False,
) -> None:
    try:
        snapshot_path = resolve_activation_snapshot(snapshot_dir, reference)
        snapshot = load_activation_snapshot(snapshot_path)
    except SnapshotError as error:
        runtime.console.print(f"[red]✗[/red] {error}")
        raise typer.Exit(1) from None

    if json_output:
        runtime.console.print_json(data=snapshot.to_dict())
        return

    runtime.console.print(f"[bold]Snapshot[/bold] {snapshot.path.name}")
    runtime.console.print(f"  [dim]Path:[/dim] {snapshot.path}")
    runtime.console.print(f"  [dim]Created:[/dim] {snapshot.created_at or '?'}")
    runtime.console.print(f"  [dim]Operation:[/dim] {snapshot.operation}")
    if snapshot.tag:
        runtime.console.print(f"  [dim]Tag:[/dim] {snapshot.tag}")
    runtime.console.print(
        f"  [dim]Counts:[/dim] {len(snapshot.found_chars)} chars, "
        f"{snapshot.note_count} notes, {snapshot.card_count} cards"
    )
    runtime.console.print(
        f"  [dim]Cards affected by undo/change:[/dim] {snapshot.mutation_card_count}"
    )
    if snapshot.found_chars:
        runtime.console.print(f"  [dim]Characters:[/dim] {_snapshot_chars_text(snapshot.found_chars)}")

    missing = snapshot.data.get("missing_chars")
    if isinstance(missing, list) and missing:
        runtime.console.print(f"  [yellow]Missing:[/yellow] {' '.join(str(char) for char in missing)}")


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

    snapshots_app = typer.Typer(
        name="snapshots",
        help="Inspect local activation undo snapshots without touching Anki.",
        no_args_is_help=True,
    )

    @snapshots_app.command("list")
    def snapshots_list_command(
        limit: int = typer.Option(
            20,
            "--limit",
            "-n",
            help="Maximum snapshots to show (0 = all).",
        ),
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Print snapshot summaries as machine-readable JSON.",
        ),
        snapshot_dir: Path = typer.Option(
            ANKI_BACKUP_DIR,
            "--dir",
            help="Snapshot directory to inspect.",
        ),
    ) -> None:
        """List local activation undo snapshots."""
        run_snapshot_list(
            runtime,
            snapshot_dir=snapshot_dir,
            limit=limit,
            json_output=json_output,
        )

    @snapshots_app.command("show")
    def snapshots_show_command(
        snapshot: str = typer.Argument(..., help="Snapshot filename, stem, or path."),
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Print the snapshot as machine-readable JSON.",
        ),
        snapshot_dir: Path = typer.Option(
            ANKI_BACKUP_DIR,
            "--dir",
            help="Snapshot directory to inspect.",
        ),
    ) -> None:
        """Show one local activation undo snapshot."""
        run_snapshot_show(
            runtime,
            snapshot,
            snapshot_dir=snapshot_dir,
            json_output=json_output,
        )

    activate_app.add_typer(snapshots_app, name="snapshots")
    app.add_typer(activate_app, name="activate")
