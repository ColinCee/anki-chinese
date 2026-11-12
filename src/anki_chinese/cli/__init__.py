"""CLI package entry point."""

from __future__ import annotations

import io
import sys
from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app import AppRuntime, app, build_runtime, create_app

__all__ = [
    "AppRuntime",
    "app",
    "build_runtime",
    "create_app",
    "main",
]


def __getattr__(name: str) -> Any:
    # Building the full app imports every command (seconds); defer it until used.
    exported = {"AppRuntime", "app", "build_runtime", "create_app"}
    if name not in exported:
        raise AttributeError(name)
    app_module = import_module(".app", __name__)
    # Importing the submodule binds `cli.app` to the module; rebind it to the Typer app.
    globals().update({export: getattr(app_module, export) for export in exported})
    return globals()[name]


def main() -> None:
    # Piped output on Windows defaults to cp1252, which cannot print hanzi.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    # A chat-tutor turn waits on this command, so it skips the full app.
    if sys.argv[1:2] == ["tutor"]:
        from .tutor import app as tutor_app

        tutor_app(args=sys.argv[2:], prog_name="anki-chinese tutor")
        return
    from .app import app as full_app

    full_app()
