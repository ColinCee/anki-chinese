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


def _write_song(
    lyrics_dir: Path,
    body: str = "一二三喵",
    *,
    file_name: str = "01-test.md",
    title: str = "测试歌",
) -> None:
    lyrics_dir.mkdir(parents=True, exist_ok=True)
    (lyrics_dir / file_name).write_text(
        textwrap.dedent("""\
            ---
            title: {title}
            artist: 测试
            ---
            {body}
        """).format(title=title, body=body),
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


def test_run_songs_next_without_song_selects_first_analyzed_song_with_new_chars(
    runtime_factory,
) -> None:
    runtime = runtime_factory(parsed_notes=[])
    _write_song(
        runtime.song_lyrics_dir,
        body="一",
        file_name="01-known.md",
        title="已会一",
    )
    _write_song(
        runtime.song_lyrics_dir,
        body="一",
        file_name="02-known.md",
        title="已会二",
    )
    _write_song(
        runtime.song_lyrics_dir,
        body="一二",
        file_name="03-next.md",
        title="下一首",
    )
    _write_song(
        runtime.song_lyrics_dir,
        body="一二三",
        file_name="04-later.md",
        title="后一首",
    )

    knowledge = StubKnowledgeClient(
        studied={"一"},
        deck_order=["一", "二", "三"],
    )

    plan = run_songs_next(
        runtime,
        lyrics_dir=runtime.song_lyrics_dir,
        limit=1,
        knowledge_client=knowledge,
    )

    output = runtime.console.file.getvalue()
    assert plan.song.title == "下一首"
    assert plan.chars == ("二",)
    assert "Skipped 2 songs with 0 new in-deck chars" in output
    assert "Auto-selected next song" in output


def test_run_songs_activate_without_song_uses_auto_selected_song(runtime_factory) -> None:
    runtime = runtime_factory(parsed_notes=[])
    _write_song(runtime.song_lyrics_dir, body="一", file_name="01-known.md", title="已会")
    _write_song(runtime.song_lyrics_dir, body="一二", file_name="02-next.md", title="下一首")

    knowledge = StubKnowledgeClient(
        studied={"一"},
        deck_order=["一", "二", "三"],
    )
    client = StubAnkiClient()

    run_songs_activate(
        runtime,
        lyrics_dir=runtime.song_lyrics_dir,
        limit=1,
        dry_run=False,
        client=client,
        knowledge_client=knowledge,
    )

    assert client.unsuspended == [20, 21]
    assert client.tags == [([2], "activated::song::下一首")]


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
