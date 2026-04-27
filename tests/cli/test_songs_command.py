from __future__ import annotations

import textwrap
from pathlib import Path

from anki_chinese.activation import LiveNoteCards
from anki_chinese.cli.songs import run_songs_activate, run_songs_next
from anki_chinese.notes import CharacterNote


class StubAnkiClient:
    def __init__(self) -> None:
        self.unsuspended: list[int] = []
        self.tags: list[tuple[list[int], str]] = []

    def find_notes_by_chars(self, chars: list[str]) -> dict[str, LiveNoteCards]:
        notes = {
            "二": LiveNoteCards(character="二", note_ids=(2,), card_ids=(20, 21)),
            "三": LiveNoteCards(character="三", note_ids=(3,), card_ids=(30, 31)),
        }
        return {char: notes[char] for char in chars if char in notes}

    def suspended_card_ids(self, card_ids: list[int]) -> set[int]:
        return set(card_ids)

    def unsuspend_cards(self, card_ids: list[int]) -> None:
        self.unsuspended.extend(card_ids)

    def add_tags(self, note_ids: list[int], tag: str) -> None:
        self.tags.append((note_ids, tag))


def _write_song(lyrics_dir: Path, body: str = "一二三喵") -> None:
    lyrics_dir.mkdir(parents=True)
    (lyrics_dir / "01-test.md").write_text(
        textwrap.dedent("""\
            ---
            title: 测试歌
            artist: 测试
            ---
            {body}
        """).format(body=body),
        encoding="utf-8",
    )


def test_run_songs_next_plans_from_export_state(runtime_factory) -> None:
    runtime = runtime_factory(
        parsed_notes=[
            CharacterNote(hanzi="一", meaning="one"),
            CharacterNote(hanzi="二", meaning="two"),
            CharacterNote(hanzi="三", meaning="three"),
        ]
    )
    runtime.load_learned_hanzi = lambda path: {"一"}
    _write_song(runtime.song_lyrics_dir)

    plan = run_songs_next(
        runtime,
        "测试歌",
        lyrics_dir=runtime.song_lyrics_dir,
        apkg_path=runtime.source_deck_path,
        limit=2,
    )

    assert set(plan.chars) == {"二", "三"}
    assert plan.non_deck_chars == ("喵",)
    assert "Next chars" in runtime.console.file.getvalue()


def test_run_songs_activate_uses_song_plan_and_activation_service(runtime_factory) -> None:
    runtime = runtime_factory(
        parsed_notes=[
            CharacterNote(hanzi="一", meaning="one"),
            CharacterNote(hanzi="二", meaning="two"),
            CharacterNote(hanzi="三", meaning="three"),
        ]
    )
    runtime.load_learned_hanzi = lambda path: {"一"}
    _write_song(runtime.song_lyrics_dir)
    client = StubAnkiClient()

    run_songs_activate(
        runtime,
        "测试歌",
        lyrics_dir=runtime.song_lyrics_dir,
        apkg_path=runtime.source_deck_path,
        limit=2,
        dry_run=False,
        client=client,
    )

    assert client.unsuspended == [20, 21, 30, 31]
    assert client.tags == [([2, 3], "activated::song::测试歌")]


def test_run_songs_next_normalizes_traditional_particle_for_planning(runtime_factory) -> None:
    runtime = runtime_factory(
        parsed_notes=[
            CharacterNote(hanzi="我", meaning="I"),
            CharacterNote(hanzi="看", meaning="to look"),
            CharacterNote(hanzi="你", meaning="you"),
            CharacterNote(hanzi="着", meaning="aspect particle"),
        ]
    )
    runtime.load_learned_hanzi = lambda path: {"我", "看", "你"}
    _write_song(runtime.song_lyrics_dir, body="我看著你")

    plan = run_songs_next(
        runtime,
        "测试歌",
        lyrics_dir=runtime.song_lyrics_dir,
        apkg_path=runtime.source_deck_path,
        limit=1,
    )

    assert plan.chars == ("着",)
    assert plan.non_deck_chars == ()
