"""`anki-chinese sync` command."""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

import typer
from rich.console import Console
from rich.table import Table

from ..workflows.sync import SyncPlan, plan_sync
from .app import AppRuntime


def _render_sync_plan(runtime: AppRuntime, plan: SyncPlan, *, dry_run_footer: bool = True) -> None:
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
    if dry_run_footer:
        runtime.console.print("[dim]Dry run only. No files changed.[/dim]")


@dataclass(frozen=True)
class SyncExecutionResult:
    executed_commands: list[str]
    final_plan: SyncPlan

    def to_dict(self) -> dict[str, object]:
        return {
            "executed_commands": self.executed_commands,
            "plan": self.final_plan.to_dict(),
        }


def _execute_sync_for_json(runtime: AppRuntime, *, skip_audio: bool) -> dict[str, object]:
    original_console = runtime.console
    log_buffer = StringIO()
    runtime.console = Console(file=log_buffer, force_terminal=False, color_system=None)
    try:
        result = _execute_sync_plan(runtime, skip_audio=skip_audio)
    finally:
        runtime.console = original_console
    data = result.to_dict()
    data["log"] = log_buffer.getvalue()
    return data


def _build_sync_plan(
    runtime: AppRuntime,
    *,
    skip_audio: bool,
) -> SyncPlan:
    return plan_sync(
        source_deck_path=runtime.source_deck_path,
        enriched_path=runtime.note_store.path,
        deck_output_path=runtime.deck_output_path,
        generated_audio_dir=runtime.generated_audio_dir,
        tts_provider=runtime.tts_provider,
        sentence_tts_provider=runtime.sentence_tts_provider,
        audio_manifest_path=runtime.audio_manifest_path,
        skip_audio=skip_audio,
        pipeline_state_path=runtime.pipeline_state_path,
    )


def _execute_stage(runtime: AppRuntime, stage_id: str) -> str:
    if stage_id == "init":
        from .init import run_init

        run_init(runtime, runtime.source_deck_path)
        return "anki-chinese init"
    if stage_id == "audio":
        from .audio import run_audio

        run_audio(runtime)
        return "anki-chinese audio"
    if stage_id == "build":
        from .build import run_build

        run_build(runtime)
        return "anki-chinese build"
    raise AssertionError(f"Unknown sync stage: {stage_id}")


def _execute_sync_plan(
    runtime: AppRuntime,
    *,
    skip_audio: bool,
) -> SyncExecutionResult:
    executed_commands: list[str] = []
    executed_stage_ids: set[str] = set()

    while True:
        plan = _build_sync_plan(runtime, skip_audio=skip_audio)
        needed_stage = next((stage for stage in plan.stages if stage.status == "needed"), None)
        if needed_stage is None:
            return SyncExecutionResult(executed_commands=executed_commands, final_plan=plan)
        if needed_stage.id in executed_stage_ids:
            runtime.console.print(
                f"[red]✗[/red] {needed_stage.command} is still needed after running. "
                "Stopping to avoid repeating a failed stage."
            )
            raise typer.Exit(1)

        runtime.console.print(f"\n[bold]Running:[/bold] {needed_stage.command}")
        executed_stage_ids.add(needed_stage.id)
        executed_commands.append(_execute_stage(runtime, needed_stage.id))


def run_sync(
    runtime: AppRuntime,
    *,
    dry_run: bool = False,
    json_output: bool = False,
    skip_audio: bool = False,
) -> SyncPlan:
    """Plan or execute sync steps for generated deck artifacts."""

    plan = _build_sync_plan(runtime, skip_audio=skip_audio)

    if not dry_run:
        if json_output:
            runtime.console.print_json(data=_execute_sync_for_json(runtime, skip_audio=skip_audio))
        else:
            result = _execute_sync_plan(runtime, skip_audio=skip_audio)
            if result.final_plan.is_up_to_date:
                runtime.console.print("[green]✓[/green] Sync complete")
            else:
                runtime.console.print("[yellow]⚠[/yellow] Sync stopped before all stages were current")
                _render_sync_plan(runtime, result.final_plan, dry_run_footer=False)
            return result.final_plan
        return _build_sync_plan(runtime, skip_audio=skip_audio)

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
            help="Print the sync plan/result as machine-readable JSON.",
        ),
        skip_audio: bool = typer.Option(
            False,
            "--skip-audio",
            help="Do not include audio generation in the sync plan.",
        ),
    ) -> None:
        """Bring generated deck artifacts up to date, or preview with --dry-run."""

        run_sync(runtime, dry_run=dry_run, json_output=json_output, skip_audio=skip_audio)
