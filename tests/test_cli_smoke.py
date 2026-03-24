from io import StringIO
from pathlib import Path

from rich.console import Console
from typer.testing import CliRunner

from anki_chinese.audio.provider import ProviderCapabilities
from anki_chinese.cli import AppRuntime, create_app
from anki_chinese.notes import CharacterNote, JsonNoteStore


runner = CliRunner()


class StubTTSProvider:
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="stub",
            supports_mandarin=True,
            supports_cantonese=True,
            supports_phoneme_control=False,
        )

    def generate_mandarin(self, hanzi: str, pinyin: str, *, force: bool = False) -> str:
        return f"[sound:cmn_{hanzi}_{pinyin}.mp3]"

    def generate_cantonese(
        self,
        hanzi: str,
        jyutping: str,
        *,
        force: bool = False,
    ) -> str:
        return f"[sound:yue_{hanzi}_{jyutping}.mp3]"

    def generate_example_audio(
        self,
        word: str,
        pinyin: str,
        *,
        force: bool = False,
    ) -> str:
        return f"[sound:cmn_{word}_{pinyin}.mp3]"

    def is_valid_audio_tag(self, tag: str) -> bool:
        return True


def _build_runtime(tmp_path: Path) -> AppRuntime:
    source_deck_path = tmp_path / "deck.txt"
    source_deck_path.write_text("placeholder\n", encoding="utf-8")
    return AppRuntime(
        source_deck_path=source_deck_path,
        note_store=JsonNoteStore(tmp_path / "enriched.json"),
        generated_media_dir=tmp_path / "generated-media",
        test_media_dir=tmp_path / "test-media",
        parse_deck_export=lambda path: [CharacterNote(hanzi="一", keyword="one")],
        enrich_notes=lambda notes, skip_examples=False: [
            CharacterNote(hanzi="一", keyword="one", pinyin="yī", jyutping="jat1")
        ],
        build_deck=lambda notes: tmp_path / "deck.apkg",
        tts_provider=StubTTSProvider(),
        console=Console(file=StringIO(), force_terminal=False, color_system=None),
    )


def test_init_command_parses_enriches_and_saves_notes(tmp_path: Path) -> None:
    runtime = _build_runtime(tmp_path)
    app = create_app(runtime)

    result = runner.invoke(app, ["init", "--input", str(runtime.source_deck_path)])

    assert result.exit_code == 0
    saved_notes = runtime.note_store.load()
    assert len(saved_notes) == 1
    assert saved_notes[0].pinyin == "yī"


def test_build_command_loads_saved_notes_and_builds_package(tmp_path: Path) -> None:
    runtime = _build_runtime(tmp_path)
    output_path = tmp_path / "deck.apkg"
    output_path.write_bytes(b"deck")
    runtime.note_store.save([CharacterNote(hanzi="一", keyword="one", pinyin="yī")])
    app = create_app(runtime)

    result = runner.invoke(app, ["build"])

    assert result.exit_code == 0
    assert output_path.exists()
