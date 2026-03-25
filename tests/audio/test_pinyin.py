from anki_chinese.audio.pinyin import diacritical_to_numbered


def test_single_tone_marks() -> None:
    assert diacritical_to_numbered("yī") == "yi1"
    assert diacritical_to_numbered("yí") == "yi2"
    assert diacritical_to_numbered("yǐ") == "yi3"
    assert diacritical_to_numbered("yì") == "yi4"


def test_neutral_tone() -> None:
    assert diacritical_to_numbered("ma") == "ma5"
    assert diacritical_to_numbered("de") == "de5"


def test_multi_syllable() -> None:
    assert diacritical_to_numbered("nǐ hǎo") == "ni3 hao3"
    assert diacritical_to_numbered("zhōng guó") == "zhong1 guo2"


def test_u_with_umlaut() -> None:
    assert diacritical_to_numbered("lǜ") == "lü4"
    assert diacritical_to_numbered("nǚ") == "nü3"
