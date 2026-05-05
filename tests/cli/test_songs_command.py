from __future__ import annotations

import textwrap
from pathlib import Path

from anki_chinese.activation import LiveNoteCards
from anki_chinese.cli.songs import run_songs_activate, run_songs_next


class StubKnowledgeClient:
    """Stub for KnowledgeClient that returns pre-set knowledge state."""

    def __init__(self, studied: set[str], deck_order: list[str]) -> None:
        self._studied = studied
        self._deck_order = deck_order

    def find_studied_characters(self) -> set[str]:
        return self._studied

    def find_all_deck_info(self) -> tuple[list[str], set[str]]:
        return self._deck_order, set(self._deck_order)


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


def test_run_songs_next_plans_from_live_state(runtime_factory) -> None:
    runtime = runtime_factory(parsed_notes=[])
    _write_song(runtime.song_lyrics_dir)

    knowledge = StubKnowledgeClient(
        studied={"一"},
        deck_order=["一", "二", "三"],
    )

    plan = run_songs_next(
        runtime,
        "测试歌",
        lyrics_dir=runtime.song_lyrics_dir,
        limit=2,
        knowledge_client=knowledge,
    )

    assert set(plan.chars) == {"二", "三"}
    assert plan.non_deck_chars == ("喵",)
    assert "Next chars" in runtime.console.file.getvalue()


def test_run_songs_activate_uses_song_plan_and_activation_service(runtime_factory) -> None:
    runtime = runtime_factory(parsed_notes=[])
    _write_song(runtime.song_lyrics_dir)

    knowledge = StubKnowledgeClient(
        studied={"一"},
        deck_order=["一", "二", "三"],
    )
    client = StubAnkiClient()

    run_songs_activate(
        runtime,
        "测试歌",
        lyrics_dir=runtime.song_lyrics_dir,
        limit=2,
        dry_run=False,
        client=client,
        knowledge_client=knowledge,
    )

    assert client.unsuspended == [20, 21, 30, 31]
    assert client.tags == [([2, 3], "activated::song::测试歌")]


def test_run_songs_next_normalizes_traditional_particle_for_planning(runtime_factory) -> None:
    runtime = runtime_factory(parsed_notes=[])
    _write_song(runtime.song_lyrics_dir, body="我看著你")

    knowledge = StubKnowledgeClient(
        studied={"我", "看", "你"},
        deck_order=["我", "看", "你", "着"],
    )

    plan = run_songs_next(
        runtime,
        "测试歌",
        lyrics_dir=runtime.song_lyrics_dir,
        limit=1,
        knowledge_client=knowledge,
    )

    assert plan.chars == ("着",)
    assert plan.non_deck_chars == ()
