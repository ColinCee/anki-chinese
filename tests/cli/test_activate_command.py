from __future__ import annotations

import json
from unittest.mock import patch

from anki_chinese.activation import LiveNoteCards
from anki_chinese.cli import create_app
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

    result = run_activate_chars(runtime, ["水"], dry_run=True, client=client)

    assert result.preview.suspended_card_ids == (10, 11)
    assert result.snapshot_path is None
    assert client.unsuspended == []
    assert "Would activate 2 cards" in runtime.console.file.getvalue()


def test_run_activate_chars_unsuspends_cards(runtime_factory, tmp_path) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="水", meaning="water")])
    client = StubAnkiClient()

    result = run_activate_chars(
        runtime,
        ["水"],
        dry_run=False,
        client=client,
        snapshot_dir=tmp_path,
    )

    assert client.unsuspended == [10, 11]
    assert result.snapshot_path is not None
    snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["operation"] == "activate-chars"
    assert snapshot["pre_change_suspended_card_ids"] == [10, 11]
    output = runtime.console.file.getvalue()
    assert "Activated 2 cards" in output
    assert "Undo snapshot:" in output


def test_activate_chars_cli_previews_without_confirm(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="水", meaning="water")])
    app = create_app(runtime)

    with patch("anki_chinese.cli.activate.run_activate_chars") as run_activate:
        result = runner.invoke(app, ["activate", "chars", "水"])

    assert result.exit_code == 0
    run_activate.assert_called_once()
    assert run_activate.call_args.kwargs["dry_run"] is True
    assert "--confirm" in runtime.console.file.getvalue()


def test_activate_chars_cli_confirm_mutates(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="水", meaning="water")])
    app = create_app(runtime)

    with patch("anki_chinese.cli.activate.run_activate_chars") as run_activate:
        result = runner.invoke(app, ["activate", "chars", "水", "--confirm"])

    assert result.exit_code == 0
    run_activate.assert_called_once()
    assert run_activate.call_args.kwargs["dry_run"] is False
