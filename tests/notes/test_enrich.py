import anki_chinese.notes.enrich as enrich_module
from anki_chinese.notes import CharacterNote


def _patch_defaults(monkeypatch, *, overrides=None):
    """Patch track (suppress progress bar) and load_overrides with common defaults."""
    monkeypatch.setattr(enrich_module, "track", lambda seq, **kw: seq)
    monkeypatch.setattr(
        enrich_module, "load_overrides", lambda path: (overrides or {})
    )


# ── Existing tests ──────────────────────────────────────────────────────


def test_enrich_uses_example_reading_for_polyphonic_character(
    monkeypatch,
) -> None:
    note = CharacterNote(hanzi="行", keyword="go")

    _patch_defaults(monkeypatch)
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

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("haang4", False))
    monkeypatch.setattr(enrich_module, "lookup_example", lambda hanzi: ("", "", ""))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("xíng", True))
    monkeypatch.setattr(enrich_module, "lookup_pinyin_word", lambda word: "")

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.pinyin == "xíng"
    assert enriched.jyutping == "haang4"
    assert enriched.needs_review
    assert "Polyphonic character" in enriched.review_reason


# ── Jyutping lookup ────────────────────────────────────────────────────


def test_jyutping_lookup_fills_missing_jyutping(monkeypatch) -> None:
    note = CharacterNote(hanzi="水", keyword="water")

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("seoi2", False))
    monkeypatch.setattr(enrich_module, "lookup_example", lambda hanzi: ("", "", ""))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("shuǐ", False))
    monkeypatch.setattr(enrich_module, "lookup_pinyin_word", lambda word: "")

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.jyutping == "seoi2"
    assert not enriched.needs_review


def test_jyutping_flags_review_when_not_found(monkeypatch) -> None:
    note = CharacterNote(hanzi="水", keyword="water")

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("", True))
    monkeypatch.setattr(enrich_module, "lookup_example", lambda hanzi: ("", "", ""))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("shuǐ", False))
    monkeypatch.setattr(enrich_module, "lookup_pinyin_word", lambda word: "")

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.jyutping == ""
    assert enriched.needs_review
    assert "No jyutping found" in enriched.review_reason


# ── Example lookup ──────────────────────────────────────────────────────


def test_example_lookup_fills_missing_fields(monkeypatch) -> None:
    note = CharacterNote(hanzi="大", keyword="big")

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("daai6", False))
    monkeypatch.setattr(
        enrich_module,
        "lookup_example",
        lambda hanzi: ("大学", "university", "dà xué"),
    )
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("dà", False))
    monkeypatch.setattr(enrich_module, "lookup_pinyin_word", lambda word: "dà xué")

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.example_word == "大学"
    assert enriched.example_meaning == "university"
    assert enriched.example_pinyin == "dà xué"


# ── Polyphonic review flag ──────────────────────────────────────────────


def test_polyphonic_character_gets_review_flag_with_correct_message(
    monkeypatch,
) -> None:
    note = CharacterNote(hanzi="乐", keyword="music")

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("lok6", False))
    monkeypatch.setattr(enrich_module, "lookup_example", lambda hanzi: ("", "", ""))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("lè", True))
    monkeypatch.setattr(enrich_module, "lookup_pinyin_word", lambda word: "")

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.pinyin == "lè"
    assert enriched.needs_review
    assert "Polyphonic character" in enriched.review_reason
    assert "defaulted to 'lè'" in enriched.review_reason


# ── Override application ────────────────────────────────────────────────


def test_override_application_changes_fields(monkeypatch) -> None:
    note = CharacterNote(hanzi="了", keyword="completed")

    _patch_defaults(
        monkeypatch,
        overrides={"了": {"pinyin": "le", "keyword": "particle"}},
    )
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("liu5", False))
    monkeypatch.setattr(enrich_module, "lookup_example", lambda hanzi: ("", "", ""))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("liǎo", False))
    monkeypatch.setattr(enrich_module, "lookup_pinyin_word", lambda word: "")

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.pinyin == "le"
    assert enriched.keyword == "particle"


# ── Example reading derivation ──────────────────────────────────────────


def test_example_reading_derivation_sets_pinyin(monkeypatch) -> None:
    """Pinyin is derived from the example word, skipping the dictionary lookup."""
    note = CharacterNote(hanzi="大", keyword="big")

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("daai6", False))
    monkeypatch.setattr(
        enrich_module,
        "lookup_example",
        lambda hanzi: ("大学", "university", "dà xué"),
    )
    # Return a wrong value — if example derivation works, this is never used.
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("WRONG", False))
    monkeypatch.setattr(enrich_module, "lookup_pinyin_word", lambda word: "dà xué")

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.pinyin == "dà"


# ── skip_examples ───────────────────────────────────────────────────────


def test_skip_examples_skips_example_lookup(monkeypatch) -> None:
    note = CharacterNote(hanzi="水", keyword="water")

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("seoi2", False))

    def fail_example(hanzi):
        raise AssertionError("lookup_example should not be called")

    monkeypatch.setattr(enrich_module, "lookup_example", fail_example)
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("shuǐ", False))
    monkeypatch.setattr(enrich_module, "lookup_pinyin_word", lambda word: "")

    [enriched] = enrich_module.enrich_notes([note], skip_examples=True)

    assert enriched.pinyin == "shuǐ"
    assert enriched.example_word == ""


# ── Two-pass _resolve_example_pinyin ────────────────────────────────────


def test_resolve_example_pinyin_runs_before_and_after_overrides(
    monkeypatch,
) -> None:
    """Override changes example_word; second pass re-derives reading from new word."""
    note = CharacterNote(hanzi="行", keyword="go")

    _patch_defaults(
        monkeypatch,
        overrides={"行": {"example_word": "银行", "example_meaning": "bank"}},
    )
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("haang4", False))
    monkeypatch.setattr(
        enrich_module,
        "lookup_example",
        lambda hanzi: ("行走", "walk", "xíng zǒu"),
    )
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("xíng", True))
    monkeypatch.setattr(
        enrich_module,
        "lookup_pinyin_word",
        lambda word: {"行走": "xíng zǒu", "银行": "yín háng"}.get(word, ""),
    )

    [enriched] = enrich_module.enrich_notes([note])

    # First pass derived "xíng" from "行走", but the override changed
    # example_word to "银行", so the second pass re-derives pinyin as "háng".
    assert enriched.pinyin == "háng"
    assert enriched.example_word == "银行"
    assert enriched.example_pinyin == "yín háng"
    assert not enriched.needs_review
