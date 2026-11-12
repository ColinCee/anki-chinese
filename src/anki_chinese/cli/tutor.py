"""`anki-chinese tutor`: what a chat-tutor session runs each turn.

`cli.main` runs this without building the full CLI; see `cli/__init__.py`.
"""

from __future__ import annotations

import time

import typer

from .. import tutor

app = typer.Typer(help="Chat tutor: known characters, voiced replies, new-character log.")


@app.command()
def say(
    lines: list[str] = typer.Argument(..., help="Chinese lines to voice, in playing order."),
    voice: str = typer.Option(tutor.TUTOR_VOICE_ID, help="MiniMax voice ID."),
    play: bool = typer.Option(True, help="Play the clips on this PC."),
) -> None:
    """Log new characters in LINES, voice them and play them."""
    start = time.perf_counter()
    known = tutor.load_known()
    new: dict[str, str] = {}
    for line in lines:
        for char in known.new_in(line):
            new.setdefault(char, line)
    tutor.log_new(new)
    paths = tutor.voice_lines(lines, voice_id=voice)
    if play and not tutor.play_in_background(paths):
        typer.echo("ffplay not found; clips not played")
    typer.echo(f"new: {' '.join(new) or '-'}")
    for path in paths:
        typer.echo(f"audio: {path}")
    typer.echo(f"took {time.perf_counter() - start:.1f}s")


@app.command()
def known(refresh: bool = typer.Option(False, help="Re-read Anki now.")) -> None:
    """Print studied and unlocked characters, and this week's new ones to reuse."""
    data = tutor.refresh_known() if refresh else tutor.load_known()
    typer.echo(f"source: {data.source}, {data.updated}")
    typer.echo(f"studied ({len(data.studied)}): {''.join(sorted(data.studied))}")
    typer.echo(f"unlocked, not reviewed ({len(data.unlocked)}): {''.join(sorted(data.unlocked))}")
    typer.echo(f"new this week: {' '.join(tutor.recent_new()) or '-'}")


@app.command()
def check(text: str) -> None:
    """Print characters in TEXT that are neither studied nor unlocked."""
    typer.echo(" ".join(tutor.load_known().new_in(text)) or "-")


def register(parent: typer.Typer) -> None:
    parent.add_typer(app, name="tutor")
