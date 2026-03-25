"""`anki-chinese test-tts` command."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.table import Table

from ..audio.factory import PROVIDER_NAMES, build_tts_provider
from ..notes.model import CharacterNote
from .app import AppRuntime


def _filename_from_sound_tag(tag: str) -> str:
    return tag.removeprefix("[sound:").removesuffix("]")


def _add_audio_row(
    table: Table,
    *,
    label: str,
    tag: str,
    audio_dir,
) -> None:
    filename = _filename_from_sound_tag(tag)
    output_path = audio_dir / filename
    table.add_row(label, filename, f"{output_path.stat().st_size:,} bytes")


def _sample_dir_for(
    runtime: AppRuntime, *, label: str, provider_name: str
) -> Path:
    """Return samples/<label>/<provider>, creating it fresh."""
    sample_dir = runtime.sample_audio_dir / label / provider_name
    if sample_dir.exists():
        shutil.rmtree(sample_dir)
    sample_dir.mkdir(parents=True, exist_ok=True)
    return sample_dir


def run_test_tts(
    runtime: AppRuntime,
    *,
    char: str = "",
    word: str = "",
    provider_name: str = "minimax",
) -> None:
    if not char and not word:
        runtime.console.print("[red]✗[/red] Pass --char or --word (or both).")
        raise typer.Exit(1)

    if char:
        sample_dir = _sample_dir_for(runtime, label=char, provider_name=provider_name)
        preview_provider = build_tts_provider(
            generated_audio_dir=sample_dir,
            provider_name=provider_name,
        )
        caps = preview_provider.capabilities()
        runtime.console.print(f"[dim]Provider:[/dim] {caps.name}")
        runtime.console.print(f"[dim]Samples:[/dim]  {sample_dir}")

        note: CharacterNote | None = None
        if runtime.note_store.exists():
            matches = [candidate for candidate in runtime.note_store.load() if candidate.hanzi == char]
            if matches:
                note = matches[0]

        if note:
            runtime.console.print(f"[blue]Testing[/blue] {note.hanzi} ({note.keyword})")
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Type", style="cyan")
            table.add_column("File")
            table.add_column("Size", justify="right", style="dim")

            if note.pinyin:
                tag = preview_provider.generate_mandarin(
                    note.hanzi,
                    note.pinyin,
                    force=True,
                )
                _add_audio_row(
                    table,
                    label="Mandarin",
                    tag=tag,
                    audio_dir=sample_dir,
                )

            if note.jyutping:
                tag = preview_provider.generate_cantonese(
                    note.hanzi,
                    note.jyutping,
                    force=True,
                )
                _add_audio_row(
                    table,
                    label="Cantonese",
                    tag=tag,
                    audio_dir=sample_dir,
                )

            if note.example_word:
                if note.example_pinyin:
                    tag = preview_provider.generate_example_audio(
                        note.example_word,
                        note.example_pinyin,
                        force=True,
                    )
                else:
                    tag = preview_provider.generate_plain_mandarin(
                        note.example_word,
                        force=True,
                    )
                _add_audio_row(
                    table,
                    label=f"Example ({note.example_word} · {note.example_pinyin or 'plain'})",
                    tag=tag,
                    audio_dir=sample_dir,
                )

            runtime.console.print(table)
        else:
            runtime.console.print(
                f"[yellow]⚠[/yellow] '{char}' not in enriched data — generating plain Mandarin audio only."
            )
            tag = preview_provider.generate_plain_mandarin(char, force=True)
            filename = _filename_from_sound_tag(tag)
            output_path = sample_dir / filename
            runtime.console.print(f"  → {output_path} ({output_path.stat().st_size:,} bytes)")

    if word:
        sample_dir = _sample_dir_for(runtime, label=word, provider_name=provider_name)
        preview_provider = build_tts_provider(
            generated_audio_dir=sample_dir,
            provider_name=provider_name,
        )
        caps = preview_provider.capabilities()
        runtime.console.print(f"[dim]Provider:[/dim] {caps.name}")
        runtime.console.print(f"[dim]Samples:[/dim]  {sample_dir}")
        runtime.console.print(f"[blue]Testing word[/blue] {word}")
        tag = preview_provider.generate_plain_mandarin(word, force=True)
        filename = _filename_from_sound_tag(tag)
        output_path = sample_dir / filename
        runtime.console.print(f"  → {output_path} ({output_path.stat().st_size:,} bytes)")


def register(app: typer.Typer, runtime: AppRuntime) -> None:
    @app.command(name="test-tts")
    def test_tts(
        char: str = typer.Option(
            "",
            "--char",
            "-c",
            help="Character to test (looks up pinyin/jyutping from enriched data).",
        ),
        word: str = typer.Option(
            "",
            "--word",
            "-w",
            help="Arbitrary Mandarin text to synthesise with the configured provider defaults.",
        ),
        provider: str = typer.Option(
            "minimax",
            "--provider",
            "-p",
            help=f"TTS provider to test ({', '.join(PROVIDER_NAMES)}).",
        ),
    ) -> None:
        """Generate test audio for a single character or word.

        Wipes the provider's samples subdirectory first so you always hear fresh audio.
        """
        run_test_tts(
            runtime,
            char=char,
            word=word,
            provider_name=provider,
        )
