from pathlib import Path

from anki_chinese.data_sources import _cedict as cedict_module
from anki_chinese.data_sources import _hsk as hsk_module


def test_hsk_extract_fields_prefers_common_sense_over_proper_noun() -> None:
    word, freq, meaning, pinyin = hsk_module._extract_fields(
        {
            "s": "温泉",
            "q": 7424,
            "f": [
                {
                    "i": {"y": "Wēn quán"},
                    "m": [
                        "Arishang Nahiyisi or Wenquan county in Börtala Mongol autonomous prefecture 博尔塔拉蒙古自治州, Xinjiang"
                    ],
                },
                {
                    "i": {"y": "wēn quán"},
                    "m": ["hot spring", "spa", "onsen"],
                },
            ],
        }
    )

    assert (word, freq, meaning, pinyin) == ("温泉", 7424, "hot spring", "wēn quán")


def test_cedict_build_index_prefers_common_sense_over_proper_noun(
    tmp_path: Path,
) -> None:
    cedict_path = tmp_path / "cedict.txt"
    cedict_path.write_text(
        "\n".join(
            [
                "溫泉 温泉 [Wen1 quan2] /Wenquan county/",
                "溫泉 温泉 [wen1 quan2] /hot spring/spa/onsen/",
            ]
        ),
        encoding="utf-8",
    )

    index = cedict_module.build_index(cedict_path)

    word, meaning, _ = index["泉"][0]
    assert (word, meaning) == ("温泉", "hot spring")
