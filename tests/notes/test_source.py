from pathlib import Path

import pytest

from anki_chinese.notes import CharacterNote, Curriculum
from anki_chinese.notes.source import (
    CharacterSourceStore,
    add_source_record,
    update_source_record,
)


def test_source_store_round_trip_preserves_curriculum(tmp_path: Path) -> None:
    path = tmp_path / "characters.json"
    notes = [
        CharacterNote(
            hanzi="一",
            meaning="one",
            curriculum=Curriculum(
                track="rsh",
                rsh_number=1,
                lesson="RSH1-L01",
                origin="rsh",
            ),
        ),
        CharacterNote(
            hanzi="睫",
            meaning="eyelashes",
            heisig_num="3019",
            curriculum=Curriculum(
                track="custom",
                origin="manual",
                collection="Manual-Missing-2026-07-02",
            ),
        ),
    ]

    store = CharacterSourceStore(path)
    store.save(notes)

    loaded = store.load()
    assert loaded == [
        notes[0],
        CharacterNote(
            hanzi="睫",
            meaning="eyelashes",
            curriculum=Curriculum(
                track="custom",
                origin="manual",
                collection="Manual-Missing-2026-07-02",
            ),
        ),
    ]


def test_source_record_rejects_duplicate_hanzi(tmp_path: Path) -> None:
    path = tmp_path / "characters.json"
    store = CharacterSourceStore(path)
    store.save([CharacterNote(hanzi="水", meaning="water")])

    with pytest.raises(ValueError, match="already"):
        add_source_record(path, CharacterNote(hanzi="水", meaning="water; liquid"))


def test_source_record_requires_complete_sentence_updates(tmp_path: Path) -> None:
    path = tmp_path / "characters.json"
    CharacterSourceStore(path).save(
        [CharacterNote(hanzi="水", meaning="water", sentence="我喝水。")]
    )

    with pytest.raises(ValueError, match="must be supplied together"):
        update_source_record(path, "水", {"sentence": "他喝水。"})


def test_source_store_validates_before_replacing_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "characters.json"
    store = CharacterSourceStore(path)
    store.save([CharacterNote(hanzi="水", meaning="water")])

    with pytest.raises(ValueError, match="Duplicate canonical character"):
        store.save([CharacterNote(hanzi="一"), CharacterNote(hanzi="一")])

    assert [note.hanzi for note in store.load()] == ["水"]
