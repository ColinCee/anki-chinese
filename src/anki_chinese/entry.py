"""`anki-chinese` console entry point.

Importing `anki_chinese.cli` builds every command (seconds). A chat-tutor turn
waits on its command, so `tutor` is dispatched before that import.
"""

from __future__ import annotations

import io
import sys


def main() -> None:
    # Piped output on Windows defaults to cp1252, which cannot print hanzi.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["tutor"]:
        from .tutor.cli import app as tutor_app

        tutor_app(args=sys.argv[2:], prog_name="anki-chinese tutor")
        return
    from .cli import app

    app()
