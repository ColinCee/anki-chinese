from anki_chinese.notes.pronunciation import (
    normalize_pinyin,
    reading_matches,
)


def test_normalize_pinyin_trims_and_lowercases() -> None:
    assert normalize_pinyin("  YIN   HANG  ") == "yin hang"


def test_reading_matches_returns_false_when_syllable_count_does_not_match_word() -> None:
    assert not reading_matches("行", "银行", "yín", "háng")


def test_reading_matches_checks_target_character_syllable() -> None:
    assert reading_matches("行", "银行", "yín háng", "háng")
    assert not reading_matches("行", "银行", "yín háng", "xíng")
