"""Helpers for CLI interactivity boundaries."""

from __future__ import annotations

import sys
from typing import NoReturn

import typer
from rich.console import Console


def is_interactive_terminal() -> bool:
    """Return whether stdin and stdout are attached to a terminal."""

    return sys.stdin.isatty() and sys.stdout.isatty()


def refuse_non_interactive(console: Console, *, action: str, hint: str) -> NoReturn:
    """Print an actionable non-interactive refusal and exit."""

    console.print(f"[red]✗[/red] {action} requires an interactive terminal. {hint}")
    raise typer.Exit(1)


def require_interactive_terminal(
    console: Console,
    *,
    action: str,
    hint: str,
    force: bool = False,
) -> None:
    """Refuse non-interactive execution unless explicitly forced."""

    if force or is_interactive_terminal():
        return
    refuse_non_interactive(console, action=action, hint=hint)
