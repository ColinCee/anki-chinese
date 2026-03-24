"""`anki-chinese test-tts` command."""

from __future__ import annotations

import typer
from rich.table import Table

from ..audio.azure import (
    _generate_audio,
    _ssml_cantonese,
    _ssml_mandarin,
    _ssml_mandarin_text,
    _ssml_plain,
)
from ..config import MANDARIN_VOICE
from ..notes.model import CharacterNote
from .app import AppRuntime


def run_test_tts(
    runtime: AppRuntime,
    *,
    char: str = "",
    word: str = "",
    voice: str = "",
    force: bool = False,
) -> None:
    if not char and not word:
        runtime.console.print("[red]✗[/red] Pass --char or --word (or both).")
        raise typer.Exit(1)

    runtime.sample_audio_dir.mkdir(parents=True, exist_ok=True)
    use_voice = voice or MANDARIN_VOICE
    voice_tag = use_voice.split("-", 2)[-1] if "-" in use_voice else use_voice
    if voice:
        runtime.console.print(f"[dim]Voice:[/dim] {use_voice}")

    if char:
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
                safe_pinyin = note.pinyin.replace(" ", "_")
                filename = f"{voice_tag}_cmn_{note.hanzi}_{safe_pinyin}.mp3"
                output_path = runtime.sample_audio_dir / filename
                if not output_path.exists() or force:
                    ssml = _ssml_mandarin(note.hanzi, note.pinyin, voice=use_voice)
                    _generate_audio(ssml, output_path)
                table.add_row("Mandarin", filename, f"{output_path.stat().st_size:,} bytes")

            if note.jyutping:
                safe_jyutping = note.jyutping.replace(" ", "_")
                filename = f"{voice_tag}_yue_{note.hanzi}_{safe_jyutping}.mp3"
                output_path = runtime.sample_audio_dir / filename
                if not output_path.exists() or force:
                    ssml = _ssml_cantonese(note.hanzi, note.jyutping)
                    _generate_audio(ssml, output_path)
                table.add_row("Cantonese", filename, f"{output_path.stat().st_size:,} bytes")

            if note.example_word:
                if note.example_pinyin:
                    safe_example_pinyin = note.example_pinyin.replace(" ", "_")
                    filename = f"{voice_tag}_cmn_{note.example_word}_{safe_example_pinyin}.mp3"
                    output_path = runtime.sample_audio_dir / filename
                    if not output_path.exists() or force:
                        ssml = _ssml_mandarin_text(
                            note.example_word,
                            note.example_pinyin,
                            voice=use_voice,
                        )
                        _generate_audio(ssml, output_path)
                else:
                    filename = f"{voice_tag}_cmn_{note.example_word}.mp3"
                    output_path = runtime.sample_audio_dir / filename
                    if not output_path.exists() or force:
                        ssml = _ssml_plain(
                            text=note.example_word,
                            voice=use_voice,
                            lang="zh-CN",
                        )
                        _generate_audio(ssml, output_path)
                table.add_row(
                    f"Example ({note.example_word} · {note.example_pinyin or 'plain'})",
                    filename,
                    f"{output_path.stat().st_size:,} bytes",
                )

            runtime.console.print(table)
        else:
            runtime.console.print(
                f"[yellow]⚠[/yellow] '{char}' not in enriched data — generating plain Mandarin audio only."
            )
            filename = f"{voice_tag}_test_{char}.mp3"
            output_path = runtime.sample_audio_dir / filename
            ssml = _ssml_plain(text=char, voice=use_voice, lang="zh-CN")
            _generate_audio(ssml, output_path)
            runtime.console.print(f"  → {output_path} ({output_path.stat().st_size:,} bytes)")

    if word:
        runtime.console.print(f"[blue]Testing word[/blue] {word}")
        filename = f"{voice_tag}_test_{word}.mp3"
        output_path = runtime.sample_audio_dir / filename

        if output_path.exists() and not force:
            runtime.console.print(
                f"  → {output_path} (cached, {output_path.stat().st_size:,} bytes)"
            )
        else:
            ssml = _ssml_plain(text=word, voice=use_voice, lang="zh-CN")
            _generate_audio(ssml, output_path)
            runtime.console.print(
                f"  → {output_path} ({output_path.stat().st_size:,} bytes)"
            )


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
            help="Arbitrary Mandarin text to synthesise (plain, no phoneme forcing).",
        ),
        voice: str = typer.Option(
            "",
            "--voice",
            "-v",
            help="Override Mandarin voice name (e.g. zh-CN-XiaoyiNeural) for comparison.",
        ),
        force: bool = typer.Option(
            False,
            "--force",
            "-f",
            help="Regenerate even if the file already exists.",
        ),
    ) -> None:
        """Generate test audio for a single character or word."""
        run_test_tts(
            runtime,
            char=char,
            word=word,
            voice=voice,
            force=force,
        )
