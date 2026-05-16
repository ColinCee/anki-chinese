from anki_chinese.notes.pronunciation import (
    find_phonetic_confuser_details,
    find_phonetic_confusers,
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


def test_find_phonetic_confusers_flags_same_base() -> None:
    assert find_phonetic_confusers("和", "hé", "我和朋友一起去喝茶", "wǒ hé péngyǒu yīqǐ qù hē chá") == [
        ("喝", "hē", "same-base")
    ]


def test_find_phonetic_confusers_flags_retroflex_pair() -> None:
    confusers = find_phonetic_confuser_details(
        "卓",
        "zhuó",
        "他的工作表现很卓越",
        "tā de gōng zuò biǎo xiàn hěn zhuó yuè",
    )

    assert [(c.character, c.pinyin, c.severity) for c in confusers] == [
        ("作", "zuò", "near-retroflex")
    ]


def test_find_phonetic_confusers_same_final_is_opt_in() -> None:
    assert (
        find_phonetic_confuser_details(
            "门",
            "mén",
            "门口有人",
            "mén kǒu yǒu rén",
        )
        == []
    )
    confusers = find_phonetic_confuser_details(
        "门",
        "mén",
        "门口有人",
        "mén kǒu yǒu rén",
        include_same_final=True,
    )

    assert [(c.character, c.pinyin, c.severity) for c in confusers] == [
        ("人", "rén", "same-final")
    ]
