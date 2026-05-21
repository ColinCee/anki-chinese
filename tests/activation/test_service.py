from __future__ import annotations

import json
from pathlib import Path

import pytest

from anki_chinese.activation import (
    LiveNoteCards,
    activate_characters,
    normalize_character_args,
    preview_tag_resuspension,
    resuspend_tagged_cards,
)


class StubAnkiClient:
    def __init__(self, snapshot_dir: Path | None = None) -> None:
        self.snapshot_dir = snapshot_dir
        self.notes = {
            "水": LiveNoteCards(character="水", note_ids=(1,), card_ids=(10, 11)),
            "火": LiveNoteCards(character="火", note_ids=(2,), card_ids=(20, 21)),
        }
        self.suspended = {10, 11}
        self.unsuspended: list[int] = []
        self.tags: list[tuple[list[int], str]] = []

    def find_notes_by_chars(self, chars: list[str]) -> dict[str, LiveNoteCards]:
        return {char: self.notes[char] for char in chars if char in self.notes}

    def suspended_card_ids(self, card_ids: list[int]) -> set[int]:
        return {card_id for card_id in card_ids if card_id in self.suspended}

    def unsuspend_cards(self, card_ids: list[int]) -> None:
        if self.snapshot_dir is not None:
            assert list(self.snapshot_dir.glob("activation-*.json"))
        self.unsuspended.extend(card_ids)

    def add_tags(self, note_ids: list[int], tag: str) -> None:
        self.tags.append((note_ids, tag))


class StubResuspendClient:
    def __init__(self, snapshot_dir: Path | None = None) -> None:
        self.snapshot_dir = snapshot_dir
        self.notes = {
            "水": LiveNoteCards(character="水", note_ids=(1,), card_ids=(10, 11)),
            "火": LiveNoteCards(character="火", note_ids=(2,), card_ids=(20, 21)),
        }
        self.suspended = {11}
        self.resuspended: list[int] = []
        self.removed_tags: list[tuple[list[int], str]] = []

    def find_notes_by_tag(self, tag: str) -> dict[str, LiveNoteCards]:
        if tag != "activated::song::test":
            return {}
        return self.notes

    def suspended_card_ids(self, card_ids: list[int]) -> set[int]:
        return {card_id for card_id in card_ids if card_id in self.suspended}

    def suspend_cards(self, card_ids: list[int]) -> None:
        if self.snapshot_dir is not None:
            assert list(self.snapshot_dir.glob("resuspend-*.json"))
        self.resuspended.extend(card_ids)
        self.suspended.update(card_ids)

    def remove_tags(self, note_ids: list[int], tag: str) -> None:
        self.removed_tags.append((note_ids, tag))


def test_normalize_character_args_extracts_unique_cjk() -> None:
    assert normalize_character_args(["水火", " 火 ", "abc山"]) == ["水", "火", "山"]


def test_activate_characters_dry_run_does_not_mutate() -> None:
    client = StubAnkiClient()

    result = activate_characters(client, ["水", "火", "山"], tag="song", dry_run=True)
    preview = result.preview

    assert preview.suspended_card_ids == (10, 11)
    assert preview.already_active_chars == ("火",)
    assert preview.missing_chars == ("山",)
    assert client.unsuspended == []
    assert client.tags == []
    assert result.snapshot_path is None


def test_activate_characters_unsuspends_suspended_cards_and_tags_notes(
    tmp_path: Path,
) -> None:
    client = StubAnkiClient(snapshot_dir=tmp_path)

    result = activate_characters(
        client,
        ["水", "火"],
        tag="song",
        dry_run=False,
        snapshot_dir=tmp_path,
    )
    preview = result.preview

    assert preview.suspended_card_ids == (10, 11)
    assert client.unsuspended == [10, 11]
    assert client.tags == [([1], "song")]
    assert result.snapshot_path is not None
    snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["operation"] == "activate-chars"
    assert snapshot["model_name"] == "Chinese RSH"
    assert snapshot["requested_chars"] == ["水", "火"]
    assert snapshot["found_chars"] == ["水", "火"]
    assert snapshot["missing_chars"] == []
    assert snapshot["already_active_chars"] == ["火"]
    assert snapshot["note_ids"] == [1]
    assert snapshot["card_ids"] == [10, 11, 20, 21]
    assert snapshot["pre_change_suspended_card_ids"] == [10, 11]
    assert snapshot["tag"] == "song"


def test_activate_characters_requires_snapshot_dir_for_mutation() -> None:
    client = StubAnkiClient()

    with pytest.raises(ValueError, match="snapshot_dir is required"):
        activate_characters(client, ["水"], dry_run=False)

    assert client.unsuspended == []


def test_preview_tag_resuspension_reports_active_and_suspended_cards() -> None:
    client = StubResuspendClient()

    preview = preview_tag_resuspension(client, "activated::song::test")

    assert preview.found_chars == ("水", "火")
    assert preview.note_ids == (1, 2)
    assert preview.card_ids == (10, 11, 20, 21)
    assert preview.already_suspended_card_ids == (11,)
    assert preview.cards_to_suspend == (10, 20, 21)
    assert preview.note_ids_to_suspend == (1, 2)


def test_resuspend_tagged_cards_dry_run_does_not_mutate(tmp_path: Path) -> None:
    client = StubResuspendClient()

    result = resuspend_tagged_cards(
        client,
        "activated::song::test",
        dry_run=True,
        snapshot_dir=tmp_path,
    )

    assert result.preview.cards_to_suspend == (10, 20, 21)
    assert result.snapshot_path is None
    assert client.resuspended == []
    assert client.removed_tags == []
    assert not list(tmp_path.glob("*.json"))


def test_resuspend_tagged_cards_writes_snapshot_before_mutation(tmp_path: Path) -> None:
    client = StubResuspendClient(snapshot_dir=tmp_path)

    result = resuspend_tagged_cards(
        client,
        "activated::song::test",
        dry_run=False,
        snapshot_dir=tmp_path,
    )

    assert result.snapshot_path is not None
    assert result.snapshot_path.exists()
    assert client.resuspended == [10, 20, 21]
    assert client.removed_tags == [([1, 2], "activated::song::test")]

    snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["operation"] == "resuspend-tagged-cards"
    assert snapshot["tag"] == "activated::song::test"
    assert snapshot["pre_change_suspended_card_ids"] == [11]
    assert snapshot["card_ids_to_suspend"] == [10, 20, 21]
    assert snapshot["note_ids_to_suspend"] == [1, 2]


def test_resuspend_tagged_cards_can_keep_tag(tmp_path: Path) -> None:
    client = StubResuspendClient()

    resuspend_tagged_cards(
        client,
        "activated::song::test",
        dry_run=False,
        remove_tag=False,
        snapshot_dir=tmp_path,
    )

    assert client.resuspended == [10, 20, 21]
    assert client.removed_tags == []
