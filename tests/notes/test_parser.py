from pathlib import Path

from anki_chinese.notes import parse_deck_export


def _write_export(path: Path, rows: list[list[str]], *, headers: list[str] | None = None) -> None:
    header_text = ""
    if headers:
        header_text = "".join(f"{line}\n" for line in headers)
    row_text = "\n".join("\t".join(row) for row in rows)
    path.write_text(f"{header_text}{row_text}\n", encoding="utf-8")


def test_parse_deck_export_supports_legacy_rows_with_image_hanzi(tmp_path: Path) -> None:
    export_path = tmp_path / "legacy.txt"
    row = [""] * 16
    row[2] = '<img src="4e00.gif" />'
    row[3] = "one"
    row[4] = "stroke.gif"
    row[5] = "story"
    row[7] = '<span class="tone1">yī</span> <!-- yi -->'
    row[10] = "RSH 1"
    row[11] = "Lesson 1"
    row[12] = "before [sound:cmn_一_yī.mp3] after"
    row[13] = '<span class="tone1">jat1</span>'
    row[14] = "[sound:yue_一_jat1.mp3]"
    _write_export(export_path, [row])

    notes = parse_deck_export(export_path)

    assert len(notes) == 1
    note = notes[0]
    assert note.hanzi == "一"
    assert note.keyword == "one"
    assert note.pinyin == "yī"
    assert note.jyutping == "jat1"
    assert note.mandarin_audio == "[sound:cmn_一_yī.mp3]"
    assert note.cantonese_audio == "[sound:yue_一_jat1.mp3]"
    assert note.heisig_num == "RSH 1"
    assert note.lesson == "Lesson 1"
    assert note.story == "story"


def test_parse_deck_export_supports_exported_rows_with_header_map(tmp_path: Path) -> None:
    export_path = tmp_path / "exported.txt"
    row = [""] * 18
    row[0] = "guid-123"
    row[1] = "Chinese RSH"
    row[2] = "Chinese"
    row[3] = "行"
    row[4] = "go"
    row[5] = '<span class="tone2">xíng</span>'
    row[6] = '<span class="tone4">haang4</span>'
    row[7] = "[sound:cmn_行_xíng.mp3]"
    row[8] = "[sound:yue_行_haang4.mp3]"
    row[9] = "银行"
    row[10] = "bank"
    row[11] = "yín háng"
    row[12] = "[sound:cmn_银行_yín_háng.mp3]"
    row[13] = "stroke-order"
    row[14] = "RSH 144"
    row[15] = "Lesson 12"
    row[16] = "walk"
    _write_export(export_path, [row], headers=["#guid column:1"])

    notes = parse_deck_export(export_path)

    assert len(notes) == 1
    note = notes[0]
    assert note.hanzi == "行"
    assert note.keyword == "go"
    assert note.pinyin == "xíng"
    assert note.jyutping == "haang4"
    assert note.stroke_order == "stroke-order"
    assert note.heisig_num == "RSH 144"
    assert note.lesson == "Lesson 12"
    assert note.story == "walk"


def test_parse_deck_export_empty_file(tmp_path: Path) -> None:
    export_path = tmp_path / "empty.txt"
    export_path.write_text("", encoding="utf-8")

    notes = parse_deck_export(export_path)

    assert notes == []


def test_parse_deck_export_empty_file_with_header_only(tmp_path: Path) -> None:
    export_path = tmp_path / "header_only.txt"
    export_path.write_text("#guid column:1\n", encoding="utf-8")

    notes = parse_deck_export(export_path)

    assert notes == []


def test_parse_deck_export_skips_malformed_short_rows(tmp_path: Path) -> None:
    export_path = tmp_path / "malformed.txt"
    short_row = ["col1", "col2", "col3"]
    good_row = [""] * 16
    good_row[2] = "水"
    good_row[3] = "water"
    good_row[7] = '<span class="tone3">shuǐ</span>'
    _write_export(export_path, [short_row, good_row])

    notes = parse_deck_export(export_path)

    assert len(notes) == 1
    assert notes[0].hanzi == "水"
    assert notes[0].keyword == "water"


def test_parse_deck_export_unicode_cjk_characters(tmp_path: Path) -> None:
    export_path = tmp_path / "unicode.txt"
    row = [""] * 16
    row[2] = "龍"
    row[3] = "dragon — 龍"
    row[5] = "story with 中文 and émojis 🐉"
    row[7] = '<span class="tone2">lóng</span>'
    row[10] = "RSH 2000"
    row[11] = "Lesson 99"
    row[13] = '<span class="tone4">lung4</span>'
    _write_export(export_path, [row])

    notes = parse_deck_export(export_path)

    assert len(notes) == 1
    note = notes[0]
    assert note.hanzi == "龍"
    assert note.keyword == "dragon — 龍"
    assert note.story == "story with 中文 and émojis 🐉"
    assert note.pinyin == "lóng"
    assert note.jyutping == "lung4"


def test_parse_deck_export_multiple_rows(tmp_path: Path) -> None:
    export_path = tmp_path / "multi.txt"
    row_a = [""] * 16
    row_a[2] = "大"
    row_a[3] = "big"
    row_a[7] = '<span class="tone4">dà</span>'

    row_b = [""] * 16
    row_b[2] = "小"
    row_b[3] = "small"
    row_b[7] = '<span class="tone3">xiǎo</span>'

    _write_export(export_path, [row_a, row_b])

    notes = parse_deck_export(export_path)

    assert len(notes) == 2
    assert notes[0].hanzi == "大"
    assert notes[1].hanzi == "小"


def test_parse_deck_export_skips_all_blank_rows(tmp_path: Path) -> None:
    """A row where every column is empty is all-whitespace and gets skipped."""
    export_path = tmp_path / "blank_fields.txt"
    blank_row = [""] * 16
    real_row = [""] * 16
    real_row[2] = "火"
    real_row[3] = "fire"
    _write_export(export_path, [blank_row, real_row])

    notes = parse_deck_export(export_path)

    assert len(notes) == 1
    assert notes[0].hanzi == "火"
