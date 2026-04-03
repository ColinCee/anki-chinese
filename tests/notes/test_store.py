from pathlib import Path

import pytest

from anki_chinese.notes import JsonNoteStore, load_notes, save_notes


def test_json_note_store_round_trip_preserves_all_fields(full_note, tmp_path: Path) -> None:
    store = JsonNoteStore(tmp_path / "nested" / "enriched.json")

    store.save([full_note])
    loaded = store.load()

    assert store.exists()
    assert loaded == [full_note]


def test_save_notes_creates_parent_directories(minimal_note, tmp_path: Path) -> None:
    path = tmp_path / "deep" / "nested" / "notes.json"

    save_notes([minimal_note], path)

    assert path.exists()


def test_load_notes_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_notes(tmp_path / "missing.json")
