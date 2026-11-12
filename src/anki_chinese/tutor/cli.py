"""`anki-chinese tutor`: what a chat-tutor session runs each turn.

Kept outside `anki_chinese.cli` so `entry.main` can run it without building
the full CLI.
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
    """Voice LINES, play them, and log characters not yet studied."""
    start = time.perf_counter()
    spoken = [line for line in dict.fromkeys(lines) if tutor.has_hanzi(line)]
    results = tutor.voice_lines(spoken, voice_id=voice)
    voiced = [path for path in results.values() if not isinstance(path, Exception)]
    if play and voiced and not tutor.play_in_background(voiced):
        typer.echo("ffplay not found; clips not played")

    new: dict[str, str] = {}
    try:
        known = tutor.load_known()
    except tutor.KnownUnavailableError as error:
        typer.echo(f"known characters unavailable: {error}")
    else:
        for line in spoken:
            for char in known.new_in(line):
                new.setdefault(char, line)
        tutor.log_new(new)

    typer.echo(f"new: {' '.join(new) or '-'}")
    for line, result in results.items():
        if isinstance(result, Exception):
            typer.echo(f"audio failed for {line}: {result}")
        else:
            typer.echo(f"audio: {result}")
    typer.echo(f"took {time.perf_counter() - start:.1f}s")


@app.command()
def known(refresh: bool = typer.Option(False, help="Re-read Anki now.")) -> None:
    """Print studied and unlocked characters, and this week's new ones to reuse."""
    try:
        data = tutor.refresh_known() if refresh else tutor.load_known()
    except tutor.KnownUnavailableError as error:
        typer.echo(f"known characters unavailable: {error}")
        raise typer.Exit(1) from error
    typer.echo(f"source: {data.source}, {data.updated}")
    typer.echo(f"studied ({len(data.studied)}): {''.join(sorted(data.studied))}")
    typer.echo(f"unlocked, not reviewed ({len(data.unlocked)}): {''.join(sorted(data.unlocked))}")
    typer.echo(f"new this week: {' '.join(tutor.recent_new()) or '-'}")


@app.command()
def check(text: str) -> None:
    """Print characters in TEXT that are neither studied nor unlocked."""
    typer.echo(" ".join(tutor.load_known().new_in(text)) or "-")


@app.command()
def serve(port: int = typer.Option(8790, help="Local port for the chat page.")) -> None:
    """Run the fast chat page: always-on Claude on your subscription, streamed voice."""
    from .server import serve as run_server

    run_server(port)


def register(parent: typer.Typer) -> None:
    parent.add_typer(app, name="tutor")
