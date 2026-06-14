from __future__ import annotations

import sqlite3
import zipfile
from copy import deepcopy
from io import StringIO
from pathlib import Path

import pytest
import zstandard as zstd
from rich.console import Console
from typer.testing import CliRunner

from anki_chinese.audio.errors import TTSRateLimitError
from anki_chinese.audio.provider import ProviderCapabilities
from anki_chinese.cli import AppRuntime
from anki_chinese.config import MODEL_ID
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

        def load_learned_hanzi(path: Path) -> set[str]:
            return set()

        def load_deck_hanzi(path: Path) -> set[str]:
            return {note.hanzi for note in parsed if len(note.hanzi) == 1}

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
            overrides_path=tmp_path / "data" / "manual" / "overrides.json",
            song_lyrics_dir=tmp_path / "data" / "songs" / "lyrics",
            hsk_vocab_path=tmp_path / "data" / "reference" / "hsk_complete.min.json",
            note_store=note_store,
            generated_audio_dir=tmp_path / "data" / "build" / "audio" / "generated",
            sample_audio_dir=tmp_path / "data" / "build" / "audio" / "samples",
            deck_output_path=output_path,
            pipeline_state_path=tmp_path / "data" / "state" / "pipeline.json",
            parse_deck_export=parse_deck_export,
            load_learned_hanzi=load_learned_hanzi,
            load_deck_hanzi=load_deck_hanzi,
            enrich_notes=enrich_notes,
            build_deck=build_deck,
            tts_provider_factory=lambda generated_audio_dir: active_tts_provider,
            tts_provider=active_tts_provider,
            console=console,
        )

    return make_runtime


_APKG_FIELD_KEYS = [
    "hanzi", "meaning", "pinyin", "jyutping",
    "mandarin_audio", "cantonese_audio",
    "stroke_order", "heisig_num", "lesson", "story",
    "sentence_audio", "sentence", "sentence_pinyin", "sentence_english",
]


def _build_test_apkg(
    path: Path,
    notes: list[dict[str, str]],
    *,
    suspended: set[str] | None = None,
    model_id: int = MODEL_ID,
    use_zstd: bool = True,
) -> Path:
    """Create a minimal .apkg file for testing."""
    suspended = suspended or set()

    tmp_db = path.parent / "_tmp_test.db"
    conn = sqlite3.connect(str(tmp_db))
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY, guid TEXT NOT NULL,
            mid INTEGER NOT NULL, mod INTEGER NOT NULL, usn INTEGER NOT NULL,
            tags TEXT NOT NULL, flds TEXT NOT NULL, sfld INTEGER NOT NULL,
            csum INTEGER NOT NULL, flags INTEGER NOT NULL, data TEXT NOT NULL
        );
        CREATE TABLE cards (
            id INTEGER PRIMARY KEY, nid INTEGER NOT NULL,
            did INTEGER NOT NULL, ord INTEGER NOT NULL,
            mod INTEGER NOT NULL, usn INTEGER NOT NULL,
            type INTEGER NOT NULL, queue INTEGER NOT NULL,
            due INTEGER NOT NULL, ivl INTEGER NOT NULL,
            factor INTEGER NOT NULL, reps INTEGER NOT NULL,
            lapses INTEGER NOT NULL, left INTEGER NOT NULL,
            odue INTEGER NOT NULL, odid INTEGER NOT NULL,
            flags INTEGER NOT NULL, data TEXT NOT NULL
        );
    """)
    card_id = 1000
    for note_id, note_data in enumerate(notes, start=1):
        flds = "\x1f".join(note_data.get(k, "") for k in _APKG_FIELD_KEYS)
        hanzi = note_data.get("hanzi", "")
        tags = note_data.get("tags", "")
        cur.execute(
            "INSERT INTO notes VALUES (?, ?, ?, 0, 0, ?, ?, ?, 0, 0, '')",
            (note_id, f"guid-{note_id}", model_id, tags, flds, note_id),
        )
        queue = -1 if hanzi in suspended else 0
        for ord_num in range(2):
            cur.execute(
                "INSERT INTO cards VALUES (?, ?, 1, ?, 0, 0, 0, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, '')",
                (card_id, note_id, ord_num, queue),
            )
            card_id += 1
    conn.commit()
    conn.close()
    sqlite_bytes = tmp_db.read_bytes()
    tmp_db.unlink()

    with zipfile.ZipFile(path, "w") as zf:
        if use_zstd:
            zf.writestr("collection.anki21b", zstd.ZstdCompressor().compress(sqlite_bytes))
        else:
            zf.writestr("collection.anki2", sqlite_bytes)
        zf.writestr("media", "{}")
    return path


@pytest.fixture
def build_test_apkg():
    return _build_test_apkg
