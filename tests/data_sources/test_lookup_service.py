from pathlib import Path

from anki_chinese import data_sources
from anki_chinese.data_sources import _cedict as cedict_module
from anki_chinese.data_sources import _hsk as hsk_module


def test_lookup_service_caches_hsk_index_by_path(monkeypatch, tmp_path: Path) -> None:
    service = data_sources.LookupService(
        example_words_path=tmp_path / "example_words.json",
        hsk_vocab_path=tmp_path / "hsk.json",
        cedict_path=tmp_path / "cedict.txt",
        subtlex_path=tmp_path / "subtlex.xlsx",
    )
    calls = {"count": 0}

    def fake_build_index(path: Path) -> dict[str, list[tuple[str, str, str]]]:
        calls["count"] += 1
        return {"行": [("银行", "bank", "yín háng")]}

    monkeypatch.setattr(hsk_module, "build_index", fake_build_index)

    assert service.lookup_example("行") == ("银行", "bank", "yín háng")
    assert service.lookup_example("行") == ("银行", "bank", "yín háng")
    assert calls["count"] == 1


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
