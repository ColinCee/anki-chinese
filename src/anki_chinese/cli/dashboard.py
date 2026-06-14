"""`anki-chinese dashboard` command."""

from __future__ import annotations

import typer

from ..tui.dashboard import run_dashboard
from .app import AppRuntime
from .interaction import require_interactive_terminal


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command()
    def dashboard(
        force: bool = typer.Option(
            False,
            "--force",
            help="Run even when stdin/stdout are not attached to a terminal.",
        ),
    ) -> None:
        """Open the interactive terminal dashboard."""

        require_interactive_terminal(
            runtime.console,
            action="The dashboard",
            hint="Use [bold]sync --dry-run --json[/bold] for agent/script workflows.",
            force=force,
        )

        run_dashboard(runtime)
