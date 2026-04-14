from pathlib import Path

from anki_chinese.notes import load_learned_hanzi_from_apkg, parse_apkg


def test_parse_apkg_extracts_all_fields(tmp_path, build_test_apkg) -> None:
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [
            {
                "hanzi": "一",
                "meaning": "one",
                "pinyin": "yī",
                "jyutping": "jat1",
                "mandarin_audio": "[sound:cmn_一_yī.mp3]",
                "cantonese_audio": "[sound:yue_一_jat1.mp3]",
                "stroke_order": '<img src="4e00.gif">',
                "heisig_num": "1",
                "lesson": "RSH1-L01",
                "story": "Like roman numeral.",
                "sentence_audio": "[sound:cmn_sentence_test.mp3]",
                "sentence": "我有一个好朋友。",
                "sentence_pinyin": "wǒ yǒu yī gè hǎo péng yǒu.",
                "sentence_english": "I have one good friend.",
            }
        ],
    )

    notes = parse_apkg(apkg)

    assert len(notes) == 1
    note = notes[0]
    assert note.hanzi == "一"
    assert note.meaning == "one"
    assert note.pinyin == "yī"
    assert note.jyutping == "jat1"
    assert note.mandarin_audio == "[sound:cmn_一_yī.mp3]"
    assert note.cantonese_audio == "[sound:yue_一_jat1.mp3]"
    assert note.stroke_order == '<img src="4e00.gif">'
    assert note.heisig_num == "1"
    assert note.lesson == "RSH1-L01"
    assert note.story == "Like roman numeral."
    assert note.sentence_audio == "[sound:cmn_sentence_test.mp3]"
    assert note.sentence == "我有一个好朋友。"
    assert note.sentence_pinyin == "wǒ yǒu yī gè hǎo péng yǒu."
    assert note.sentence_english == "I have one good friend."


def test_parse_apkg_handles_image_hanzi(tmp_path, build_test_apkg) -> None:
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [{"hanzi": '<img src="4e00.gif">', "meaning": "one"}],
    )

    notes = parse_apkg(apkg)

    assert notes[0].hanzi == "一"


def test_parse_apkg_handles_plain_text_hanzi(tmp_path, build_test_apkg) -> None:
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [{"hanzi": "水", "meaning": "water"}],
    )

    notes = parse_apkg(apkg)

    assert notes[0].hanzi == "水"


def test_parse_apkg_multiple_notes(tmp_path, build_test_apkg) -> None:
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [
            {"hanzi": "大", "meaning": "big", "heisig_num": "1"},
            {"hanzi": "小", "meaning": "small", "heisig_num": "2"},
        ],
    )

    notes = parse_apkg(apkg)

    assert len(notes) == 2
    assert notes[0].hanzi == "大"
    assert notes[1].hanzi == "小"


def test_parse_apkg_empty_deck(tmp_path, build_test_apkg) -> None:
    apkg = build_test_apkg(tmp_path / "test.apkg", [])

    notes = parse_apkg(apkg)

    assert notes == []


def test_parse_apkg_filters_by_model_id(tmp_path, build_test_apkg) -> None:
    """Notes from other notetypes are excluded."""
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [{"hanzi": "一", "meaning": "one"}],
        model_id=99999999,
    )

    notes = parse_apkg(apkg)

    assert notes == []


def test_parse_apkg_reads_uncompressed_anki2(tmp_path, build_test_apkg) -> None:
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [{"hanzi": "水", "meaning": "water"}],
        use_zstd=False,
    )

    notes = parse_apkg(apkg)

    assert len(notes) == 1
    assert notes[0].hanzi == "水"


def test_parse_apkg_unicode_characters(tmp_path, build_test_apkg) -> None:
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [{"hanzi": "龍", "meaning": "dragon — 龍", "story": "story with 中文 🐉"}],
    )

    notes = parse_apkg(apkg)

    assert notes[0].hanzi == "龍"
    assert notes[0].meaning == "dragon — 龍"
    assert notes[0].story == "story with 中文 🐉"


def test_parse_apkg_uses_tags_for_lesson(tmp_path, build_test_apkg) -> None:
    """When tags are present in the note, they take precedence for lesson."""
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [{"hanzi": "一", "meaning": "one", "lesson": "RSH1-L01", "tags": "RSH1-L01"}],
    )

    notes = parse_apkg(apkg)

    assert notes[0].lesson == "RSH1-L01"


# -- Learned hanzi (suspend status) -------------------------------------------


def test_load_learned_hanzi_returns_unsuspended_chars(tmp_path, build_test_apkg) -> None:
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [
            {"hanzi": "水", "meaning": "water"},
            {"hanzi": "火", "meaning": "fire"},
            {"hanzi": "山", "meaning": "mountain"},
        ],
        suspended={"火"},
    )

    learned = load_learned_hanzi_from_apkg(apkg)

    assert learned == {"水", "山"}


def test_load_learned_hanzi_all_suspended(tmp_path, build_test_apkg) -> None:
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [
            {"hanzi": "水", "meaning": "water"},
            {"hanzi": "火", "meaning": "fire"},
        ],
        suspended={"水", "火"},
    )

    learned = load_learned_hanzi_from_apkg(apkg)

    assert learned == set()


def test_load_learned_hanzi_none_suspended(tmp_path, build_test_apkg) -> None:
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [
            {"hanzi": "水", "meaning": "water"},
            {"hanzi": "火", "meaning": "fire"},
        ],
    )

    learned = load_learned_hanzi_from_apkg(apkg)

    assert learned == {"水", "火"}


def test_load_learned_hanzi_filters_by_model_id(tmp_path, build_test_apkg) -> None:
    """Notes from other notetypes are excluded from learned set."""
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [{"hanzi": "水", "meaning": "water"}],
        model_id=99999999,
    )

    learned = load_learned_hanzi_from_apkg(apkg)

    assert learned == set()


def test_load_learned_hanzi_with_image_hanzi(tmp_path, build_test_apkg) -> None:
    apkg = build_test_apkg(
        tmp_path / "test.apkg",
        [{"hanzi": '<img src="6c34.gif">', "meaning": "water"}],
    )

    learned = load_learned_hanzi_from_apkg(apkg)

    assert learned == {"水"}


def test_parse_real_apkg() -> None:
    """Regression test: parse the actual .apkg and verify first note."""
    apkg_path = Path(__file__).resolve().parents[2] / "data" / "source" / "All Decks.apkg"
    if not apkg_path.exists():
        return  # skip if data not available (CI)

    notes = parse_apkg(apkg_path)

    assert len(notes) > 100
    note = notes[0]
    assert note.hanzi == "一"
    assert note.meaning
    assert note.pinyin == "yī"
    assert note.jyutping == "jat1"
    assert "[sound:cmn_" in note.mandarin_audio
    assert "[sound:yue_" in note.cantonese_audio
    assert note.heisig_num == "1"
    assert note.lesson.startswith("RSH")


def test_load_learned_from_real_apkg() -> None:
    """Regression test: verify learned chars can be loaded from real .apkg."""
    apkg_path = Path(__file__).resolve().parents[2] / "data" / "source" / "All Decks.apkg"
    if not apkg_path.exists():
        return

    learned = load_learned_hanzi_from_apkg(apkg_path)

    assert len(learned) > 50
    assert "一" in learned  # basic char should be learned
