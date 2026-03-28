from anki_chinese.notes import CharacterNote
from anki_chinese.notes.report import (
    coverage_rows,
    filter_from_rsh,
    flagged_notes,
    heisig_index,
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
