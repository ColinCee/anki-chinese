from pathlib import Path

from anki_chinese.notes import CharacterNote
from anki_chinese.notes.report import (
    coverage_rows,
    filter_from_rsh,
    flagged_notes,
    heisig_index,
    load_learned_hanzi,
    prioritize_learned,
    validation_issues,
)


def test_heisig_index_extracts_numeric_portion() -> None:
    assert heisig_index(CharacterNote(heisig_num='RSH 144')) == 144
    assert heisig_index(CharacterNote(heisig_num='')) is None


def test_filter_from_rsh_returns_notes_at_or_after_requested_index() -> None:
    notes = [
        CharacterNote(hanzi='一', heisig_num='RSH 1'),
        CharacterNote(hanzi='二', heisig_num='RSH 20'),
        CharacterNote(hanzi='三', heisig_num=''),
    ]

    filtered = filter_from_rsh(notes, 10)

    assert [note.hanzi for note in filtered] == ['二']


def test_flagged_notes_returns_only_notes_marked_for_review() -> None:
    notes = [
        CharacterNote(hanzi='一'),
        CharacterNote(hanzi='行', needs_review=True, review_reason='Check reading'),
    ]

    flagged = flagged_notes(notes)

    assert [note.hanzi for note in flagged] == ['行']


def test_coverage_rows_calculates_filled_missing_and_percentages() -> None:
    notes = [
        CharacterNote(hanzi='一', keyword='one', pinyin='yī'),
        CharacterNote(hanzi='二', keyword='two'),
    ]

    rows = {label: (filled, missing, pct) for label, filled, missing, pct in coverage_rows(notes)}

    assert rows['Hanzi'] == (2, 0, 100.0)
    assert rows['Pinyin'] == (1, 1, 50.0)
    assert rows['Sentence'] == (0, 2, 0.0)


def test_validation_issues_reports_duplicates_and_dependent_field_problems() -> None:
    notes = [
        CharacterNote(hanzi='一', keyword='one'),
        CharacterNote(
            hanzi='一',
            keyword='',
            mandarin_audio='[sound:cmn_一_yī.mp3]',
            cantonese_audio='[sound:yue_一_jat1.mp3]',
            example_word='银行',
            example_audio='[sound:cmn_银行_yín_háng.mp3]',
        ),
    ]

    issues = validation_issues(notes)

    assert "Duplicate '一' at #0 and #1" in issues
    assert '#1 (一): missing keyword' in issues
    assert '#0 (一): missing pinyin' in issues
    assert '#1 (一): audio without pinyin' in issues
    assert '#1 (一): audio without jyutping' in issues
    assert '#1 (一): example word without example pinyin' in issues
    assert '#1 (一): example audio without example pinyin' in issues


# -- Learned character prioritization -----------------------------------------


def test_load_learned_hanzi_parses_anki_export(tmp_path: Path) -> None:
    export = tmp_path / "learned.txt"
    export.write_text(
        "# comment line\n"
        "col0\tcol1\tcol2\t水\n"
        "col0\tcol1\tcol2\t火\n"
        "col0\tcol1\tcol2\t山\n",
        encoding="utf-8",
    )

    result = load_learned_hanzi(export)

    assert result == {"水", "火", "山"}


def test_load_learned_hanzi_returns_empty_for_missing_file(tmp_path: Path) -> None:
    result = load_learned_hanzi(tmp_path / "nonexistent.txt")

    assert result == set()


def test_load_learned_hanzi_skips_comment_and_blank_lines(tmp_path: Path) -> None:
    export = tmp_path / "learned.txt"
    export.write_text(
        "# header\n"
        "\n"
        "col0\tcol1\tcol2\t水\n"
        "# another comment\n"
        "\n"
        "col0\tcol1\tcol2\t火\n",
        encoding="utf-8",
    )

    result = load_learned_hanzi(export)

    assert result == {"水", "火"}


def test_load_learned_hanzi_skips_rows_with_too_few_columns(tmp_path: Path) -> None:
    export = tmp_path / "learned.txt"
    export.write_text("col0\tcol1\n" "col0\tcol1\tcol2\t水\n", encoding="utf-8")

    result = load_learned_hanzi(export)

    assert result == {"水"}


def test_prioritize_learned_puts_learned_chars_first() -> None:
    notes = [
        CharacterNote(hanzi="一"),
        CharacterNote(hanzi="水"),
        CharacterNote(hanzi="火"),
        CharacterNote(hanzi="山"),
    ]
    learned = {"水", "山"}

    result = prioritize_learned(notes, learned)

    assert [n.hanzi for n in result] == ["水", "山", "一", "火"]


def test_prioritize_learned_preserves_relative_order() -> None:
    notes = [
        CharacterNote(hanzi="A"),
        CharacterNote(hanzi="B"),
        CharacterNote(hanzi="C"),
        CharacterNote(hanzi="D"),
    ]
    learned = {"D", "B"}

    result = prioritize_learned(notes, learned)

    # B before D (both learned, original order preserved)
    # A before C (both unlearned, original order preserved)
    assert [n.hanzi for n in result] == ["B", "D", "A", "C"]


def test_prioritize_learned_with_empty_learned_set() -> None:
    notes = [CharacterNote(hanzi="一"), CharacterNote(hanzi="二")]

    result = prioritize_learned(notes, set())

    assert [n.hanzi for n in result] == ["一", "二"]


def test_prioritize_learned_all_learned() -> None:
    notes = [CharacterNote(hanzi="水"), CharacterNote(hanzi="火")]

    result = prioritize_learned(notes, {"水", "火"})

    assert [n.hanzi for n in result] == ["水", "火"]
