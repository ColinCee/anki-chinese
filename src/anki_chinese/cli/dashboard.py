"""Interactive terminal workbench commands."""

from __future__ import annotations

import typer

from ..tui.dashboard import run_dashboard
from .app import AppRuntime
from .interaction import require_interactive_terminal


def _open_workbench(runtime: AppRuntime, *, force: bool, action: str) -> None:
    require_interactive_terminal(
        runtime.console,
        action=action,
        hint="Use [bold]sync --dry-run --json[/bold] for agent/script workflows.",
        force=force,
    )

    run_dashboard(runtime)


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command("workbench")
    def workbench(
        force: bool = typer.Option(
            False,
            "--force",
            help="Run even when stdin/stdout are not attached to a terminal.",
        ),
    ) -> None:
        """Open the interactive terminal workbench."""

        _open_workbench(runtime, force=force, action="The workbench")

    @app.command()
    def dashboard(
        force: bool = typer.Option(
            False,
            "--force",
            help="Run even when stdin/stdout are not attached to a terminal.",
        ),
    ) -> None:
        """Open the interactive terminal workbench."""

        _open_workbench(runtime, force=force, action="The dashboard")
