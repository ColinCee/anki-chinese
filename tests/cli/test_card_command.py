from __future__ import annotations

import json
import os
from io import StringIO

from anki_chinese.cli import create_app
from anki_chinese.cli.card import run_card_set
from anki_chinese.notes import CharacterNote, load_overrides, save_overrides


def test_card_show_json_includes_note_and_override(runtime_factory, runner) -> None:
    runtime = runtime_factory(
        saved_notes=[CharacterNote(hanzi="水", meaning="water", pinyin="shuǐ")]
    )
    save_overrides({"水": {"meaning": "water; liquid"}}, runtime.overrides_path)
    app = create_app(runtime)

    result = runner.invoke(app, ["card", "show", "水", "--json"])

    assert result.exit_code == 0
    payload = json.loads(runtime.console.file.getvalue())  # type: ignore[union-attr]
    assert payload["hanzi"] == "水"
    assert payload["note"]["pinyin"] == "shuǐ"
    assert payload["override"] == {"meaning": "water; liquid"}


def test_card_show_reports_missing_saved_note(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[])
    app = create_app(runtime)

    result = runner.invoke(app, ["card", "show", "水"])

    assert result.exit_code == 0
    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    assert "not in saved enriched state" in output


def test_card_set_writes_override_and_clears_sentence_audio(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="水", meaning="water")])
    app = create_app(runtime)

    result = runner.invoke(
        app,
        [
            "card",
            "set",
            "水",
            "--meaning",
            "water; liquid",
            "--sentence",
            "我喝水。",
            "--sentence-pinyin",
            "wǒ hē shuǐ.",
            "--sentence-english",
            "I drink water.",
        ],
    )

    assert result.exit_code == 0
    overrides = load_overrides(runtime.overrides_path)
    assert overrides["水"] == {
        "meaning": "water; liquid",
        "sentence": "我喝水。",
        "sentence_pinyin": "wǒ hē shuǐ.",
        "sentence_english": "I drink water.",
        "sentence_audio": "",
    }
    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    assert "sync --dry-run" in output


def test_card_set_makes_sync_plan_require_init(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="水", meaning="water")])
    os.utime(runtime.source_deck_path, (90, 90))
    os.utime(runtime.note_store.path, (100, 100))
    app = create_app(runtime)

    set_result = runner.invoke(app, ["card", "set", "水", "--meaning", "water; liquid"])
    os.utime(runtime.overrides_path, (110, 110))
    console_file = runtime.console.file
    assert isinstance(console_file, StringIO)
    console_file.seek(0)
    console_file.truncate(0)
    sync_result = runner.invoke(app, ["sync", "--dry-run", "--json"])

    assert set_result.exit_code == 0
    assert sync_result.exit_code == 0
    payload = json.loads(console_file.getvalue())
    assert payload["required_commands"] == ["anki-chinese init"]


def test_card_set_merges_existing_override(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="水", meaning="water")])
    save_overrides({"水": {"pinyin": "shuǐ"}}, runtime.overrides_path)

    run_card_set(runtime, "水", meaning="water; liquid")

    assert load_overrides(runtime.overrides_path)["水"] == {
        "pinyin": "shuǐ",
        "meaning": "water; liquid",
    }


def test_card_set_refuses_empty_update(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="水", meaning="water")])
    app = create_app(runtime)

    result = runner.invoke(app, ["card", "set", "水"])

    assert result.exit_code == 1
    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    assert "No override fields supplied" in output
