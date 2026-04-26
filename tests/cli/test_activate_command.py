from __future__ import annotations

from anki_chinese.activation import LiveNoteCards
from anki_chinese.cli.activate import run_activate_chars
from anki_chinese.notes import CharacterNote


class StubAnkiClient:
    def __init__(self) -> None:
        self.unsuspended: list[int] = []

    def find_notes_by_chars(self, chars: list[str]) -> dict[str, LiveNoteCards]:
        return {
            "水": LiveNoteCards(character="水", note_ids=(1,), card_ids=(10, 11)),
        }

    def suspended_card_ids(self, card_ids: list[int]) -> set[int]:
        return set(card_ids)

    def unsuspend_cards(self, card_ids: list[int]) -> None:
        self.unsuspended.extend(card_ids)

    def add_tags(self, note_ids: list[int], tag: str) -> None:
        return None


def test_run_activate_chars_dry_run_reports_cards(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="水", meaning="water")])
    client = StubAnkiClient()

    preview = run_activate_chars(runtime, ["水"], dry_run=True, client=client)

    assert preview.suspended_card_ids == (10, 11)
    assert client.unsuspended == []
    assert "Would activate 2 cards" in runtime.console.file.getvalue()


def test_run_activate_chars_unsuspends_cards(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="水", meaning="water")])
    client = StubAnkiClient()

    run_activate_chars(runtime, ["水"], dry_run=False, client=client)

    assert client.unsuspended == [10, 11]
    assert "Activated 2 cards" in runtime.console.file.getvalue()
