from __future__ import annotations

import json
import textwrap
from pathlib import Path

from anki_chinese.activation import LiveNoteCards
from anki_chinese.cli.songs import run_songs_activate, run_songs_next, run_songs_resuspend


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
        self.resuspended: list[int] = []
        self.tags: list[tuple[list[int], str]] = []
        self.removed_tags: list[tuple[list[int], str]] = []
        self.suspended: set[int] | None = None
        self.tagged_chars: dict[str, tuple[str, ...]] = {}

    def find_notes_by_chars(self, chars: list[str]) -> dict[str, LiveNoteCards]:
        notes = {
            "二": LiveNoteCards(character="二", note_ids=(2,), card_ids=(20, 21)),
            "三": LiveNoteCards(character="三", note_ids=(3,), card_ids=(30, 31)),
        }
        return {char: notes[char] for char in chars if char in notes}

    def suspended_card_ids(self, card_ids: list[int]) -> set[int]:
        if self.suspended is None:
            return set(card_ids)
        return {card_id for card_id in card_ids if card_id in self.suspended}

    def unsuspend_cards(self, card_ids: list[int]) -> None:
        self.unsuspended.extend(card_ids)

    def suspend_cards(self, card_ids: list[int]) -> None:
        self.resuspended.extend(card_ids)
        if self.suspended is None:
            self.suspended = set()
        self.suspended.update(card_ids)

    def add_tags(self, note_ids: list[int], tag: str) -> None:
        self.tags.append((note_ids, tag))

    def remove_tags(self, note_ids: list[int], tag: str) -> None:
        self.removed_tags.append((note_ids, tag))

    def find_notes_by_tag(self, tag: str) -> dict[str, LiveNoteCards]:
        chars = self.tagged_chars.get(tag, ())
        return self.find_notes_by_chars(list(chars))


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


def test_run_songs_resuspend_uses_default_song_tag_and_snapshot(runtime_factory, tmp_path) -> None:
    runtime = runtime_factory(parsed_notes=[])
    _write_song(runtime.song_lyrics_dir)
    client = StubAnkiClient()
    client.suspended = {21}
    client.tagged_chars = {"activated::song::测试歌": ("二", "三")}
    snapshot_dir = tmp_path / "snapshots"

    result = run_songs_resuspend(
        runtime,
        "测试歌",
        lyrics_dir=runtime.song_lyrics_dir,
        dry_run=False,
        snapshot_dir=snapshot_dir,
        client=client,
    )

    assert client.resuspended == [20, 30, 31]
    assert client.removed_tags == [([2, 3], "activated::song::测试歌")]
    assert result.snapshot_path is not None
    snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["tag"] == "activated::song::测试歌"
    assert snapshot["pre_change_suspended_card_ids"] == [21]
    assert snapshot["card_ids_to_suspend"] == [20, 30, 31]
    output = runtime.console.file.getvalue()
    assert "Resuspended 3 cards across 2 notes" in output
    assert "Removed tag from 2 notes" in output


def test_run_songs_resuspend_dry_run_does_not_mutate(runtime_factory, tmp_path) -> None:
    runtime = runtime_factory(parsed_notes=[])
    _write_song(runtime.song_lyrics_dir)
    client = StubAnkiClient()
    client.suspended = set()
    client.tagged_chars = {"activated::song::测试歌": ("二",)}

    result = run_songs_resuspend(
        runtime,
        "测试歌",
        lyrics_dir=runtime.song_lyrics_dir,
        dry_run=True,
        snapshot_dir=tmp_path,
        client=client,
    )

    assert result.snapshot_path is None
    assert client.resuspended == []
    assert client.removed_tags == []
    assert "Would resuspend 2 cards across 1 notes" in runtime.console.file.getvalue()


def test_run_songs_resuspend_custom_tag_can_keep_tag(runtime_factory, tmp_path) -> None:
    runtime = runtime_factory(parsed_notes=[])
    _write_song(runtime.song_lyrics_dir)
    client = StubAnkiClient()
    client.suspended = set()
    client.tagged_chars = {"batch::mistake": ("二",)}

    run_songs_resuspend(
        runtime,
        "测试歌",
        lyrics_dir=runtime.song_lyrics_dir,
        dry_run=False,
        tag="batch::mistake",
        keep_tag=True,
        snapshot_dir=tmp_path,
        client=client,
    )

    assert client.resuspended == [20, 21]
    assert client.removed_tags == []
    assert "Kept activation tag" in runtime.console.file.getvalue()


def test_run_songs_resuspend_no_tagged_notes_is_noop(runtime_factory, tmp_path) -> None:
    runtime = runtime_factory(parsed_notes=[])
    _write_song(runtime.song_lyrics_dir)
    client = StubAnkiClient()

    result = run_songs_resuspend(
        runtime,
        "测试歌",
        lyrics_dir=runtime.song_lyrics_dir,
        dry_run=False,
        snapshot_dir=tmp_path,
        client=client,
    )

    assert result.snapshot_path is None
    assert client.resuspended == []
    assert client.removed_tags == []
    assert "No tagged notes found" in runtime.console.file.getvalue()
