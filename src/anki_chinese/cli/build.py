"""`anki-chinese build` command."""

from __future__ import annotations

from pathlib import Path

import typer

from .app import AppRuntime
from .audio import run_audio
from .init import run_init


def run_build(
    runtime: AppRuntime,
    *,
    full: bool = False,
    skip_audio: bool = False,
    skip_examples: bool = False,
    audio_limit: int = 0,
    audio_start_rsh: int = 0,
) -> Path:
    if full:
        runtime.console.print("\n[bold]Step 1/3 · Parse + Enrich[/bold]")
        notes = run_init(
            runtime,
            runtime.source_deck_path,
            skip_examples=skip_examples,
        )

        if not skip_audio:
            runtime.console.print("\n[bold]Step 2/3 · Audio[/bold]")
            notes = run_audio(
                runtime,
                all_notes=notes,
                limit=audio_limit,
                start_rsh=audio_start_rsh,
            )
        else:
            runtime.console.print("\n[bold]Step 2/3 · Audio[/bold] [dim](skipped)[/dim]")

        runtime.console.print("\n[bold]Step 3/3 · Build[/bold]")
        output_path = runtime.build_deck(notes)
        runtime.console.print(f"  [green]✓[/green] {output_path} ({len(notes)} notes)\n")
        return output_path

    notes = runtime.note_store.load()
    output_path = runtime.build_deck(notes)
    runtime.console.print(f"[green]✓[/green] Built {output_path} ({len(notes)} notes)")
    return output_path


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command()
    def build(
        full: bool = typer.Option(
            False,
            "--full",
            help="Run the complete pipeline: init → audio → build.",
        ),
        skip_audio: bool = typer.Option(
            False,
            "--skip-audio",
            help="When using --full, skip the audio step.",
        ),
        skip_examples: bool = typer.Option(
            False,
            "--skip-examples",
            help="When using --full, skip example-word lookup.",
        ),
        audio_limit: int = typer.Option(
            0,
            "--audio-limit",
            help="When using --full, limit audio generation to N notes.",
        ),
        audio_start_rsh: int = typer.Option(
            0,
            "--audio-start-rsh",
            help="When using --full, start audio generation from this Heisig/RSH number.",
        ),
    ) -> None:
        """Build the .apkg deck from enriched data."""
        run_build(
            runtime,
            full=full,
            skip_audio=skip_audio,
            skip_examples=skip_examples,
            audio_limit=audio_limit,
            audio_start_rsh=audio_start_rsh,
        )
