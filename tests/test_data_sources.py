from pathlib import Path

from anki_chinese import data_sources
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
