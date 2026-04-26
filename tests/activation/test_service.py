from __future__ import annotations

from anki_chinese.activation import LiveNoteCards, activate_characters, normalize_character_args


class StubAnkiClient:
    def __init__(self) -> None:
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
        self.unsuspended.extend(card_ids)

    def add_tags(self, note_ids: list[int], tag: str) -> None:
        self.tags.append((note_ids, tag))


def test_normalize_character_args_extracts_unique_cjk() -> None:
    assert normalize_character_args(["水火", " 火 ", "abc山"]) == ["水", "火", "山"]


def test_activate_characters_dry_run_does_not_mutate() -> None:
    client = StubAnkiClient()

    preview = activate_characters(client, ["水", "火", "山"], tag="song", dry_run=True)

    assert preview.suspended_card_ids == (10, 11)
    assert preview.already_active_chars == ("火",)
    assert preview.missing_chars == ("山",)
    assert client.unsuspended == []
    assert client.tags == []


def test_activate_characters_unsuspends_suspended_cards_and_tags_notes() -> None:
    client = StubAnkiClient()

    preview = activate_characters(client, ["水", "火"], tag="song", dry_run=False)

    assert preview.suspended_card_ids == (10, 11)
    assert client.unsuspended == [10, 11]
    assert client.tags == [([1], "song")]
