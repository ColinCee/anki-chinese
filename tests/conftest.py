from __future__ import annotations

from copy import deepcopy
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from anki_chinese.audio.errors import TTSRateLimitError
from anki_chinese.audio.provider import ProviderCapabilities
from anki_chinese.cli import AppRuntime
from anki_chinese.notes import CharacterNote, JsonNoteStore


class StubTTSProvider:
    def __init__(
        self,
        *,
        valid_audio_tags: set[str] | None = None,
        rate_limit_on: set[str] | None = None,
    ) -> None:
        self.valid_audio_tags = set(valid_audio_tags or [])
        self.rate_limit_on = set(rate_limit_on or [])
        self.calls: list[tuple[str, str, str, bool]] = []

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="stub",
            supports_mandarin=True,
            supports_cantonese=True,
            supports_phoneme_control=False,
        )

    def _maybe_rate_limit(self, kind: str, key: str) -> None:
        if f"{kind}:{key}" in self.rate_limit_on:
            raise TTSRateLimitError("rate limited")

    def generate_mandarin(self, hanzi: str, pinyin: str, *, force: bool = False) -> str:
        self._maybe_rate_limit("mandarin", hanzi)
        tag = f"[sound:cmn_{hanzi}_{pinyin.replace(' ', '_')}.mp3]"
        self.valid_audio_tags.add(tag)
        self.calls.append(("mandarin", hanzi, pinyin, force))
        return tag

    def generate_plain_mandarin(self, text: str, *, force: bool = False) -> str:
        self._maybe_rate_limit("mandarin", text)
        tag = f"[sound:preview_cmn_{text.replace(' ', '_')}.mp3]"
        self.valid_audio_tags.add(tag)
        self.calls.append(("plain-mandarin", text, "", force))
        return tag

    def generate_cantonese(
        self,
        hanzi: str,
        jyutping: str,
        *,
        force: bool = False,
    ) -> str:
        self._maybe_rate_limit("cantonese", hanzi)
        tag = f"[sound:yue_{hanzi}_{jyutping.replace(' ', '_')}.mp3]"
        self.valid_audio_tags.add(tag)
        self.calls.append(("cantonese", hanzi, jyutping, force))
        return tag

    def generate_sentence_audio(
        self,
        hanzi: str,
        sentence: str,
        *,
        force: bool = False,
    ) -> str:
        self._maybe_rate_limit("sentence", hanzi)
        tag = f"[sound:cmn_sentence_{sentence}.mp3]"
        self.valid_audio_tags.add(tag)
        self.calls.append(("sentence", hanzi, sentence, force))
        return tag

    def is_valid_audio_tag(self, tag: str) -> bool:
        return tag in self.valid_audio_tags


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def minimal_note() -> CharacterNote:
    return CharacterNote(hanzi="一", meaning="one")


@pytest.fixture
def full_note() -> CharacterNote:
    return CharacterNote(
        hanzi="行",
        meaning="go",
        pinyin="xíng",
        jyutping="haang4",
        mandarin_audio="[sound:cmn_行_xíng.mp3]",
        cantonese_audio="[sound:yue_行_haang4.mp3]",
        stroke_order="stroke-order",
        heisig_num="RSH 144",
        lesson="Lesson 12",
        story="walk",
        needs_review=True,
        review_reason="Verify manually",
    )


@pytest.fixture
def stub_tts_provider() -> StubTTSProvider:
    return StubTTSProvider()


@pytest.fixture
def runtime_factory(tmp_path: Path):
    def make_runtime(
        *,
        parsed_notes: list[CharacterNote] | None = None,
        enriched_notes: list[CharacterNote] | None = None,
        saved_notes: list[CharacterNote] | None = None,
        tts_provider: StubTTSProvider | None = None,
        build_bytes: bytes = b"deck",
    ) -> AppRuntime:
        source_deck_path = tmp_path / "data" / "source" / "deck.txt"
        source_deck_path.parent.mkdir(parents=True, exist_ok=True)
        source_deck_path.write_text("placeholder\n", encoding="utf-8")
        note_store = JsonNoteStore(tmp_path / "data" / "state" / "enriched.json")
        if saved_notes is not None:
            note_store.save(deepcopy(saved_notes))

        parsed = deepcopy(parsed_notes or [CharacterNote(hanzi="一", meaning="one")])
        enriched = deepcopy(
            enriched_notes
            or [CharacterNote(hanzi="一", meaning="one", pinyin="yī", jyutping="jat1")]
        )
        output_path = tmp_path / "data" / "build" / "decks" / "deck.apkg"
        console = Console(file=StringIO(), force_terminal=False, color_system=None)

        def parse_deck_export(path: Path) -> list[CharacterNote]:
            return deepcopy(parsed)

        def enrich_notes(
            notes: list[CharacterNote],
        ) -> list[CharacterNote]:
            return deepcopy(enriched)

        def build_deck(notes: list[CharacterNote]) -> Path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(build_bytes)
            return output_path

        active_tts_provider = tts_provider or StubTTSProvider()

        return AppRuntime(
            source_deck_path=source_deck_path,
            note_store=note_store,
            generated_audio_dir=tmp_path / "data" / "build" / "audio" / "generated",
            sample_audio_dir=tmp_path / "data" / "build" / "audio" / "samples",
            parse_deck_export=parse_deck_export,
            enrich_notes=enrich_notes,
            build_deck=build_deck,
            tts_provider_factory=lambda generated_audio_dir: active_tts_provider,
            tts_provider=active_tts_provider,
            console=console,
        )

    return make_runtime
