"""`anki-chinese dashboard` command."""

from __future__ import annotations

import sys

import typer

from ..tui.dashboard import run_dashboard
from .app import AppRuntime


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

        if not force and not (sys.stdin.isatty() and sys.stdout.isatty()):
            runtime.console.print(
                "[red]✗[/red] The dashboard is interactive and requires a terminal. "
                "Use [bold]sync --dry-run --json[/bold] for agent/script workflows."
            )
            raise typer.Exit(1)

        run_dashboard(runtime)
