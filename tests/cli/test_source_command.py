import pytest
import typer

from anki_chinese.cli import create_app
from anki_chinese.cli.source import run_source_import
from anki_chinese.notes import CharacterNote
from anki_chinese.notes.source import CharacterSourceStore


def test_source_import_requires_replace_for_existing_source(runtime_factory) -> None:
    runtime = runtime_factory(parsed_notes=[CharacterNote(hanzi="一", meaning="one")])
    runtime.source_records_path = runtime.source_deck_path.parent / "characters.json"
    CharacterSourceStore(runtime.source_records_path).save([])

    with pytest.raises(typer.Exit):
        run_source_import(runtime, runtime.source_deck_path)

    assert "already exists" in runtime.console.file.getvalue()  # type: ignore[union-attr]


def test_source_import_dry_run_does_not_write(runtime_factory) -> None:
    runtime = runtime_factory(parsed_notes=[CharacterNote(hanzi="一", meaning="one")])
    runtime.source_records_path = runtime.source_deck_path.parent / "characters.json"

    count = run_source_import(runtime, runtime.source_deck_path, dry_run=True)

    assert count == 1
    assert not runtime.source_records_path.exists()


def test_source_import_is_registered(runtime_factory, runner) -> None:
    runtime = runtime_factory(parsed_notes=[CharacterNote(hanzi="一", meaning="one")])
    runtime.source_records_path = runtime.source_deck_path.parent / "characters.json"
    app = create_app(runtime)

    result = runner.invoke(
        app,
        ["source", "import", "--input", str(runtime.source_deck_path), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "Would import 1 records" in runtime.console.file.getvalue()  # type: ignore[union-attr]


def test_source_import_rejects_invalid_records_without_replacing_source(runtime_factory) -> None:
    runtime = runtime_factory(
        parsed_notes=[CharacterNote(hanzi="一"), CharacterNote(hanzi="一")]
    )
    runtime.source_records_path = runtime.source_deck_path.parent / "characters.json"
    CharacterSourceStore(runtime.source_records_path).save([CharacterNote(hanzi="水")])

    with pytest.raises(typer.Exit):
        run_source_import(runtime, runtime.source_deck_path, replace=True)

    assert [note.hanzi for note in CharacterSourceStore(runtime.source_records_path).load()] == ["水"]
