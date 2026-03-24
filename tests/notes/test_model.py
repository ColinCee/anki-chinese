from pathlib import Path

from anki_chinese.notes import CharacterNote, apply_overrides, load_overrides


def test_character_note_round_trips_through_dict_and_ignores_unknown_fields(full_note) -> None:
    restored = CharacterNote.from_dict({**full_note.to_dict(), 'unknown': 'ignored'})

    assert restored == full_note


def test_apply_overrides_updates_known_fields_only() -> None:
    note = CharacterNote(hanzi='行', keyword='go')

    apply_overrides(note, {'行': {'pinyin': 'xíng', 'unknown': 'ignored'}})

    assert note.pinyin == 'xíng'
    assert not hasattr(note, 'unknown')


def test_load_overrides_returns_empty_mapping_for_missing_file(tmp_path: Path) -> None:
    assert load_overrides(tmp_path / 'missing.json') == {}


def test_load_overrides_reads_json_mapping(tmp_path: Path) -> None:
    path = tmp_path / 'overrides.json'
    path.write_text('{"行": {"pinyin": "xíng"}}', encoding='utf-8')

    assert load_overrides(path) == {'行': {'pinyin': 'xíng'}}
