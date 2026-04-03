import anki_chinese.notes.enrich as enrich_module
from anki_chinese.notes import CharacterNote


def _patch_defaults(monkeypatch, *, overrides=None):
    """Patch track (suppress progress bar) and load_overrides with common defaults."""
    monkeypatch.setattr(enrich_module, "track", lambda seq, **kw: seq)
    monkeypatch.setattr(enrich_module, "load_overrides", lambda path: overrides or {})


# ── Pinyin lookup ───────────────────────────────────────────────────────


def test_enrich_fills_missing_pinyin(monkeypatch) -> None:
    note = CharacterNote(hanzi="大", meaning="big")

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("daai6", False))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("dà", False))

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.pinyin == "dà"
    assert not enriched.needs_review


def test_enrich_marks_polyphonic_character_for_review_when_usage_is_missing(
    monkeypatch,
) -> None:
    note = CharacterNote(hanzi="行", meaning="go")

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("haang4", False))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("xíng", True))

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.pinyin == "xíng"
    assert enriched.jyutping == "haang4"
    assert enriched.needs_review
    assert "Polyphonic character" in enriched.review_reason


# ── Jyutping lookup ────────────────────────────────────────────────────


def test_jyutping_lookup_fills_missing_jyutping(monkeypatch) -> None:
    note = CharacterNote(hanzi="水", meaning="water")

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("seoi2", False))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("shuǐ", False))

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.jyutping == "seoi2"
    assert not enriched.needs_review


def test_jyutping_flags_review_when_not_found(monkeypatch) -> None:
    note = CharacterNote(hanzi="水", meaning="water")

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("", True))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("shuǐ", False))

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.jyutping == ""
    assert enriched.needs_review
    assert "No jyutping found" in enriched.review_reason


# ── Polyphonic review flag ──────────────────────────────────────────────


def test_polyphonic_character_gets_review_flag_with_correct_message(
    monkeypatch,
) -> None:
    note = CharacterNote(hanzi="乐", meaning="music")

    _patch_defaults(monkeypatch)
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("lok6", False))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("lè", True))

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.pinyin == "lè"
    assert enriched.needs_review
    assert "Polyphonic character" in enriched.review_reason
    assert "defaulted to 'lè'" in enriched.review_reason


# ── Override application ────────────────────────────────────────────────


def test_override_application_changes_fields(monkeypatch) -> None:
    note = CharacterNote(hanzi="了", meaning="completed")

    _patch_defaults(
        monkeypatch,
        overrides={"了": {"pinyin": "le", "meaning": "particle"}},
    )
    monkeypatch.setattr(enrich_module, "lookup_jyutping", lambda hanzi: ("liu5", False))
    monkeypatch.setattr(enrich_module, "lookup_pinyin", lambda hanzi: ("liǎo", False))

    [enriched] = enrich_module.enrich_notes([note])

    assert enriched.pinyin == "le"
    assert enriched.meaning == "particle"
