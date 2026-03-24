from anki_chinese.notes import CharacterNote
import anki_chinese.notes.enrich as enrich_module


def test_enrich_uses_example_reading_for_polyphonic_character(
    monkeypatch,
) -> None:
    note = CharacterNote(hanzi="行", keyword="go")

    monkeypatch.setattr(enrich_module, "load_overrides", lambda path: {})
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("haang4", False))
    monkeypatch.setattr(
        enrich_module,
        "lookup_example",
        lambda hanzi: ("银行", "bank", "yín háng"),
    )
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("xíng", True))
    monkeypatch.setattr(
        enrich_module,
        "lookup_pinyin_word",
        lambda word: "yín háng",
    )

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.example_word == "银行"
    assert enriched.example_meaning == "bank"
    assert enriched.example_pinyin == "yín háng"
    assert enriched.pinyin == "háng"
    assert enriched.jyutping == "haang4"
    assert not enriched.needs_review
    assert enriched.review_reason == ""


def test_enrich_marks_polyphonic_character_for_review_when_usage_is_missing(
    monkeypatch,
) -> None:
    note = CharacterNote(hanzi="行", keyword="go")

    monkeypatch.setattr(enrich_module, "load_overrides", lambda path: {})
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("haang4", False))
    monkeypatch.setattr(enrich_module, "lookup_example", lambda hanzi: ("", "", ""))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("xíng", True))
    monkeypatch.setattr(enrich_module, "lookup_pinyin_word", lambda word: "")

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.pinyin == "xíng"
    assert enriched.jyutping == "haang4"
    assert enriched.needs_review
    assert "Polyphonic character" in enriched.review_reason
