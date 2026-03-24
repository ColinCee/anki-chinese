from anki_chinese.config import CEDICT_PATH, HSK_VOCAB_PATH
from anki_chinese.data_sources._cedict import build_index as build_cedict_index
from anki_chinese.data_sources._hsk import build_index as build_hsk_index


def _assert_entry_shape(entry: tuple[str, str, str]) -> None:
    word, meaning, pinyin = entry
    assert isinstance(word, str)
    assert word
    assert isinstance(meaning, str)
    assert isinstance(pinyin, str)


def test_lookup_indexes_load_and_return_expected_shapes() -> None:
    hsk = build_hsk_index(HSK_VOCAB_PATH)
    cedict = build_cedict_index(CEDICT_PATH)

    assert len(hsk) > 1000
    assert len(cedict) > 1000

    samples = ["一", "人", "大", "小", "上", "学", "行"]

    assert all(hsk.get(char) for char in samples)
    assert all(cedict.get(char) for char in samples)

    for char in samples:
        h_entries = hsk.get(char, [])
        c_entries = cedict.get(char, [])
        if h_entries:
            _assert_entry_shape(h_entries[0])
        if c_entries:
            _assert_entry_shape(c_entries[0])
