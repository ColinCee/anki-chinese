from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from anki_chinese.activation import LiveNoteCards
from anki_chinese.cli import create_app
from anki_chinese.cli.activate import run_activate_chars
from anki_chinese.notes import CharacterNote


class StubAnkiClient:
    def __init__(self) -> None:
        self.suspended: set[int] = {10, 11}
        self.unsuspended: list[int] = []
        self.resuspended: list[int] = []
        self.removed_tags: list[tuple[list[int], str]] = []

    def find_notes_by_chars(self, chars: list[str]) -> dict[str, LiveNoteCards]:
        return {
            "水": LiveNoteCards(character="水", note_ids=(1,), card_ids=(10, 11)),
        }

    def suspended_card_ids(self, card_ids: list[int]) -> set[int]:
        return {card_id for card_id in card_ids if card_id in self.suspended}

    def unsuspend_cards(self, card_ids: list[int]) -> None:
        self.unsuspended.extend(card_ids)
        self.suspended.difference_update(card_ids)

    def suspend_cards(self, card_ids: list[int]) -> None:
        self.resuspended.extend(card_ids)
        self.suspended.update(card_ids)

    def add_tags(self, note_ids: list[int], tag: str) -> None:
        return None

    def remove_tags(self, note_ids: list[int], tag: str) -> None:
        self.removed_tags.append((note_ids, tag))


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


def _write_activation_snapshot(snapshot_dir: Path) -> Path:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_dir / "activation-20260101-010000.json"
    path.write_text(
        json.dumps(
            {
                "created_at": "2026-01-01T01:00:00Z",
                "operation": "activate-chars",
                "requested_chars": ["水"],
                "found_chars": ["水"],
                "missing_chars": [],
                "already_active_chars": [],
                "note_ids": [1],
                "card_ids": [10, 11],
                "pre_change_suspended_card_ids": [10, 11],
                "tag": "batch::test",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_activate_snapshots_list_json(runtime_factory, runner, tmp_path: Path) -> None:
    _write_activation_snapshot(tmp_path)
    runtime = runtime_factory()
    app = create_app(runtime)

    result = runner.invoke(
        app,
        ["activate", "snapshots", "list", "--dir", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    data = json.loads(runtime.console.file.getvalue())  # type: ignore[union-attr]
    assert data[0]["filename"] == "activation-20260101-010000.json"
    assert data[0]["mutation_card_count"] == 2


def test_activate_snapshots_show_human_output(runtime_factory, runner, tmp_path: Path) -> None:
    _write_activation_snapshot(tmp_path)
    runtime = runtime_factory()
    app = create_app(runtime)

    result = runner.invoke(
        app,
        [
            "activate",
            "snapshots",
            "show",
            "activation-20260101-010000",
            "--dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    output = runtime.console.file.getvalue()
    assert "Snapshot" in output
    assert "activate-chars" in output
    assert "batch::test" in output
    assert "2" in output


def test_activate_undo_cli_previews_without_confirm(
    runtime_factory,
    runner,
    tmp_path: Path,
) -> None:
    _write_activation_snapshot(tmp_path)
    runtime = runtime_factory()
    app = create_app(runtime)
    client = StubAnkiClient()
    client.suspended = set()

    with patch("anki_chinese.cli.activate.AnkiConnectClient", return_value=client):
        result = runner.invoke(
            app,
            ["activate", "undo", "activation-20260101-010000", "--dir", str(tmp_path)],
        )

    assert result.exit_code == 0
    assert client.resuspended == []
    output = runtime.console.file.getvalue()
    assert "Would restore by suspending 2 cards" in output
    assert "--confirm" in output


def test_activate_undo_cli_confirm_mutates(
    runtime_factory,
    runner,
    tmp_path: Path,
) -> None:
    _write_activation_snapshot(tmp_path)
    runtime = runtime_factory()
    app = create_app(runtime)
    client = StubAnkiClient()
    client.suspended = set()

    with patch("anki_chinese.cli.activate.AnkiConnectClient", return_value=client):
        result = runner.invoke(
            app,
            [
                "activate",
                "undo",
                "activation-20260101-010000",
                "--dir",
                str(tmp_path),
                "--confirm",
            ],
        )

    assert result.exit_code == 0
    assert client.resuspended == [10, 11]
    assert client.removed_tags == [([1], "batch::test")]
    assert list(tmp_path.glob("restore-*.json"))
    assert "Restored by suspending 2 cards" in runtime.console.file.getvalue()


def test_activate_undo_cli_json_is_clean_preview(
    runtime_factory,
    runner,
    tmp_path: Path,
) -> None:
    _write_activation_snapshot(tmp_path)
    runtime = runtime_factory()
    app = create_app(runtime)
    client = StubAnkiClient()
    client.suspended = set()

    with patch("anki_chinese.cli.activate.AnkiConnectClient", return_value=client):
        result = runner.invoke(
            app,
            [
                "activate",
                "undo",
                "latest",
                "--dir",
                str(tmp_path),
                "--json",
            ],
        )

    assert result.exit_code == 0
    data = json.loads(runtime.console.file.getvalue())  # type: ignore[union-attr]
    assert data["dry_run"] is True
    assert data["cards_to_suspend"] == [10, 11]
    assert client.resuspended == []
