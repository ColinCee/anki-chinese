"""Interactive terminal dashboard for human workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ..audio import TTSProvider
from ..notes import JsonNoteStore
from ..workflows.sync import SyncPlan, plan_sync


class DashboardRuntime(Protocol):
    source_deck_path: Path
    overrides_path: Path
    note_store: JsonNoteStore
    generated_audio_dir: Path
    deck_output_path: Path
    pipeline_state_path: Path
    audio_manifest_path: Path
    tts_provider: TTSProvider
    sentence_tts_provider: TTSProvider | None
    console: Console


@dataclass(frozen=True)
class MenuItem:
    key: str
    label: str
    detail: str
    commands: tuple[str, ...] = ()
    safety: str = ""


_MENU_ITEMS = [
    MenuItem("1", "Sync & rebuild", "Show the current init/audio/build plan"),
    MenuItem(
        "2",
        "Review / edit cards",
        "Inspect cards, write manual overrides, then let sync rebuild what changed",
        (
            "uv run anki-chinese status",
            "uv run anki-chinese review",
            "uv run anki-chinese card show <hanzi>",
            "uv run anki-chinese card set <hanzi> --sentence ...",
            "uv run anki-chinese sync --dry-run",
        ),
    ),
    MenuItem(
        "3",
        "Generate sentences/audio",
        "Generate or repair content, then refresh stale audio and deck output",
        (
            "uv run anki-chinese sentences --char <hanzi>",
            "uv run anki-chinese keywords",
            "uv run anki-chinese audio",
            "uv run anki-chinese sync --dry-run",
        ),
    ),
    MenuItem(
        "4",
        "Song study planner",
        "Use the high-level learn/undo workflow for human song study",
        (
            "uv run anki-chinese songs analyze",
            "uv run anki-chinese songs next --limit 20",
            "uv run anki-chinese songs learn --limit 20",
            "uv run anki-chinese songs learn --limit 20 --confirm",
            "uv run anki-chinese songs undo",
        ),
        "Live Anki changes preview by default; use --confirm only after reviewing counts.",
    ),
    MenuItem(
        "5",
        "Activate / unsuspend in Anki",
        "Preview explicit character activation before mutating live Anki",
        (
            "uv run anki-chinese activate chars <chars> --dry-run",
            "uv run anki-chinese activate chars <chars> --confirm",
            "uv run anki-chinese activate snapshots list",
            "uv run anki-chinese activate undo latest",
        ),
        "Confirmed activation writes an undo snapshot before unsuspending cards.",
    ),
    MenuItem(
        "6",
        "Health, cleanup, undo",
        "Check deck/audio health and inspect reversible live-state snapshots",
        (
            "uv run anki-chinese status",
            "uv run anki-chinese audio-clean",
            "uv run anki-chinese activate snapshots list",
            "uv run anki-chinese activate snapshots show <snapshot>",
        ),
        "Snapshot inspection is local-file only; undo previews before live changes.",
    ),
]


def _current_sync_plan(runtime: DashboardRuntime) -> SyncPlan:
    return plan_sync(
        source_deck_path=runtime.source_deck_path,
        overrides_path=runtime.overrides_path,
        enriched_path=runtime.note_store.path,
        deck_output_path=runtime.deck_output_path,
        generated_audio_dir=runtime.generated_audio_dir,
        tts_provider=runtime.tts_provider,
        sentence_tts_provider=runtime.sentence_tts_provider,
        audio_manifest_path=runtime.audio_manifest_path,
        pipeline_state_path=runtime.pipeline_state_path,
    )


def _sync_summary(plan: SyncPlan) -> str:
    needed = sum(1 for stage in plan.stages if stage.status == "needed")
    blocked = sum(1 for stage in plan.stages if stage.status == "blocked")
    skipped = sum(1 for stage in plan.stages if stage.status == "skipped")
    if plan.is_up_to_date:
        return "[green]up to date[/green]"
    parts: list[str] = []
    if needed:
        parts.append(f"[yellow]{needed} needed[/yellow]")
    if blocked:
        parts.append(f"[red]{blocked} blocked[/red]")
    if skipped:
        parts.append(f"[dim]{skipped} skipped[/dim]")
    return ", ".join(parts)


def _render_header(runtime: DashboardRuntime, plan: SyncPlan) -> None:
    next_step = plan.required_commands[0] if plan.required_commands else "No sync steps required"
    runtime.console.print(
        Panel.fit(
            "\n".join(
                [
                    "[bold]anki-chinese[/bold]",
                    f"Sync: {_sync_summary(plan)}",
                    f"Recommended: [bold]{next_step}[/bold]",
                ]
            ),
            title="Dashboard",
        )
    )


def _render_menu(runtime: DashboardRuntime) -> None:
    table = Table(show_header=False)
    table.add_column("Choice", style="cyan", width=6)
    table.add_column("Workflow")
    table.add_column("Detail", style="dim")
    for item in _MENU_ITEMS:
        table.add_row(item.key, item.label, item.detail)
    table.add_row("q", "Quit", "")
    runtime.console.print(table)


def _render_sync_plan(runtime: DashboardRuntime, plan: SyncPlan) -> None:
    table = Table(title="Sync plan")
    table.add_column("Stage", style="cyan")
    table.add_column("Status")
    table.add_column("Reason")
    for stage in plan.stages:
        table.add_row(stage.label, stage.status, stage.reason)
    runtime.console.print(table)
    if plan.required_commands:
        runtime.console.print("\n[bold]Next commands:[/bold]")
        for command in plan.required_commands:
            runtime.console.print(f"  {command}")
    else:
        runtime.console.print("\n[green]✓[/green] No sync steps required")


def _render_workflow_guidance(runtime: DashboardRuntime, item: MenuItem) -> None:
    runtime.console.print(f"\n[bold]{item.label}[/bold]")
    runtime.console.print(f"[dim]{item.detail}[/dim]")
    if item.commands:
        runtime.console.print("\n[bold]Useful commands:[/bold]")
        for command in item.commands:
            runtime.console.print(f"  {command}")
    if item.safety:
        runtime.console.print(f"\n[yellow]Safety:[/yellow] {item.safety}")


def run_dashboard(runtime: DashboardRuntime) -> None:
    """Run the interactive dashboard loop."""

    choices = [item.key for item in _MENU_ITEMS] + ["q"]
    items_by_key = {item.key: item for item in _MENU_ITEMS}

    while True:
        plan = _current_sync_plan(runtime)
        _render_header(runtime, plan)
        _render_menu(runtime)
        try:
            choice = Prompt.ask(
                "Choose a workflow",
                choices=choices,
                default="1",
                console=runtime.console,
            )
        except EOFError:
            runtime.console.print("[yellow]Input ended; exiting dashboard.[/yellow]")
            return
        if choice == "q":
            runtime.console.print("[green]Goodbye.[/green]")
            return
        if choice == "1":
            _render_sync_plan(runtime, plan)
        else:
            _render_workflow_guidance(runtime, items_by_key[choice])
