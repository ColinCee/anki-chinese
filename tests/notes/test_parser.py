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
    assert note.example_word == "银行"
    assert note.example_meaning == "bank"
    assert note.example_pinyin == "yín háng"
    assert note.example_audio == "[sound:cmn_银行_yín_háng.mp3]"
    assert note.stroke_order == "stroke-order"
    assert note.heisig_num == "RSH 144"
    assert note.lesson == "Lesson 12"
    assert note.story == "walk"
