from anki_chinese.notes import CharacterNote
from anki_chinese.notes.pronunciation import (
    normalize_example_pinyin,
    normalize_pinyin,
    reading_from_example,
    reading_matches,
)


def test_normalize_pinyin_trims_and_lowercases() -> None:
    assert normalize_pinyin('  YIN   HANG  ') == 'yin hang'


def test_reading_matches_returns_false_when_syllable_count_does_not_match_word() -> None:
    assert not reading_matches('行', '银行', 'yín', 'háng')


def test_reading_matches_checks_target_character_syllable() -> None:
    assert reading_matches('行', '银行', 'yín háng', 'háng')
    assert not reading_matches('行', '银行', 'yín háng', 'xíng')


def test_reading_from_example_returns_single_reading_when_usage_is_unambiguous() -> None:
    note = CharacterNote(hanzi='行', example_word='银行', example_pinyin='yín háng')

    assert reading_from_example(note) == 'háng'


def test_reading_from_example_returns_empty_for_multiple_different_readings() -> None:
    note = CharacterNote(hanzi='行', example_word='行行', example_pinyin='xíng háng')

    assert reading_from_example(note) == ''


def test_normalize_example_pinyin_fills_missing_value_from_lookup() -> None:
    note = CharacterNote(hanzi='行', example_word='银行')

    normalize_example_pinyin(note, lambda word: 'yín háng')

    assert note.example_pinyin == 'yín háng'


def test_normalize_example_pinyin_replaces_bad_syllable_shape_with_lookup() -> None:
    note = CharacterNote(hanzi='行', example_word='银行', example_pinyin='yin')

    normalize_example_pinyin(note, lambda word: 'yín háng')

    assert note.example_pinyin == 'yín háng'


def test_normalize_example_pinyin_replaces_mismatched_readings_with_lookup() -> None:
    note = CharacterNote(hanzi='行', example_word='银行', example_pinyin='xíng xíng')

    normalize_example_pinyin(note, lambda word: 'yín háng')

    assert note.example_pinyin == 'yín háng'
