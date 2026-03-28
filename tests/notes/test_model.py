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


def test_sentence_fields_round_trip_through_dict() -> None:
    note = CharacterNote(
        hanzi='水',
        keyword='water',
        sentence='我喝水。',
        sentence_pinyin='wǒ hē shuǐ.',
        sentence_english='I drink water.',
        sentence_keyword='water',
        sentence_audio='[sound:cmn_sentence_我喝水。.mp3]',
    )

    restored = CharacterNote.from_dict(note.to_dict())

    assert restored.sentence == '我喝水。'
    assert restored.sentence_pinyin == 'wǒ hē shuǐ.'
    assert restored.sentence_english == 'I drink water.'
    assert restored.sentence_keyword == 'water'
    assert restored.sentence_audio == '[sound:cmn_sentence_我喝水。.mp3]'


def test_to_fields_list_includes_sentence_fields() -> None:
    note = CharacterNote(
        hanzi='水',
        keyword='water',
        sentence='我喝水。',
        sentence_pinyin='wǒ hē shuǐ.',
        sentence_english='I drink water.',
        sentence_keyword='water',
        sentence_audio='[sound:cmn_sentence_我喝水。.mp3]',
    )
    fields = note.to_fields_list()

    # Sentence fields should all be present in the fields list
    assert '我喝水。' in fields
    assert 'wǒ hē shuǐ.' in fields
    assert 'I drink water.' in fields
    assert 'water' in fields  # sentence_keyword
    assert '[sound:cmn_sentence_我喝水。.mp3]' in fields
