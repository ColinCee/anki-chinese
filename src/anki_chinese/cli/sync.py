"""`anki-chinese sync` command."""

from __future__ import annotations

import typer
from rich.table import Table

from ..workflows.sync import SyncPlan, plan_sync
from .app import AppRuntime


def _render_sync_plan(runtime: AppRuntime, plan: SyncPlan) -> None:
    table = Table(title="Sync dry run")
    table.add_column("Stage", style="cyan")
    table.add_column("Status")
    table.add_column("Reason")
    table.add_column("Command")

    status_style = {
        "needed": "yellow",
        "up_to_date": "green",
        "blocked": "red",
        "skipped": "dim",
    }
    for stage in plan.stages:
        style = status_style[stage.status]
        table.add_row(
            stage.label,
            f"[{style}]{stage.status}[/{style}]",
            stage.reason,
            stage.command if stage.status == "needed" else "",
        )

    runtime.console.print(table)
    if plan.required_commands:
        runtime.console.print("\n[bold]Next commands:[/bold]")
        for command in plan.required_commands:
            runtime.console.print(f"  {command}")
    else:
        runtime.console.print("\n[green]✓[/green] No sync steps required")
    runtime.console.print("[dim]Dry run only. No files changed.[/dim]")


def run_sync(
    runtime: AppRuntime,
    *,
    dry_run: bool = False,
    json_output: bool = False,
    skip_audio: bool = False,
) -> SyncPlan:
    """Plan sync steps for generated deck artifacts."""

    plan = plan_sync(
        source_deck_path=runtime.source_deck_path,
        overrides_path=runtime.overrides_path,
        enriched_path=runtime.note_store.path,
        deck_output_path=runtime.deck_output_path,
        generated_audio_dir=runtime.generated_audio_dir,
        is_valid_audio_tag=runtime.tts_provider.is_valid_audio_tag,
        skip_audio=skip_audio,
        pipeline_state_path=runtime.pipeline_state_path,
    )

    if not dry_run:
        message = "Sync execution is not implemented yet; re-run with --dry-run to preview only."
        if json_output:
            runtime.console.print_json(data={"error": message, "plan": plan.to_dict()})
        else:
            _render_sync_plan(runtime, plan)
            runtime.console.print(f"[yellow]{message}[/yellow]")
        raise typer.Exit(1)

    if json_output:
        runtime.console.print_json(data=plan.to_dict())
    else:
        _render_sync_plan(runtime, plan)

    return plan


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command()
    def sync(
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Preview required sync steps without changing files.",
        ),
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Print the sync plan as machine-readable JSON.",
        ),
        skip_audio: bool = typer.Option(
            False,
            "--skip-audio",
            help="Do not include audio generation in the sync plan.",
        ),
    ) -> None:
        """Plan the steps needed to bring generated deck artifacts up to date."""

        run_sync(runtime, dry_run=dry_run, json_output=json_output, skip_audio=skip_audio)
