from pathlib import Path

import anki_chinese.audio.files as audio_files
from anki_chinese.audio.files import (
    audio_tasks_for_note,
    collect_orphaned_audio,
    example_audio_filename,
    expected_cantonese_audio_tag,
    expected_example_audio_tag,
    expected_mandarin_audio_tag,
    expected_sentence_audio_tag,
    is_valid_audio_tag,
    preview_mandarin_filename,
    referenced_audio_files,
    remove_orphaned_audio,
    sentence_audio_filename,
)
from anki_chinese.notes import CharacterNote


def test_expected_audio_tags_are_empty_when_required_fields_are_missing() -> None:
    note = CharacterNote(hanzi='一', keyword='one')

    assert expected_mandarin_audio_tag(note) == ''
    assert expected_cantonese_audio_tag(note) == ''
    assert expected_example_audio_tag(note) == ''
    assert expected_sentence_audio_tag(note) == ''


def test_audio_tasks_for_note_skips_valid_existing_audio() -> None:
    note = CharacterNote(
        hanzi='行',
        keyword='go',
        pinyin='xíng',
        jyutping='haang4',
        example_word='银行',
        example_pinyin='yín háng',
        mandarin_audio='[sound:cmn_行_xíng.mp3]',
        cantonese_audio='[sound:yue_行_haang4.mp3]',
        example_audio='[sound:cmn_银行_yín_háng.mp3]',
    )

    tasks = audio_tasks_for_note(
        note,
        force=False,
        is_valid_audio_tag_fn=lambda tag: True,
    )

    assert tasks == []


def test_audio_tasks_for_note_requests_missing_or_invalid_audio() -> None:
    note = CharacterNote(
        hanzi='行',
        keyword='go',
        pinyin='xíng',
        jyutping='haang4',
        example_word='银行',
        example_pinyin='yín háng',
    )

    tasks = audio_tasks_for_note(
        note,
        force=False,
        is_valid_audio_tag_fn=lambda tag: False,
    )

    assert tasks == ['mandarin', 'cantonese', 'example']


def test_audio_tasks_for_note_force_regenerates_available_audio() -> None:
    note = CharacterNote(
        hanzi='行',
        keyword='go',
        pinyin='xíng',
        jyutping='haang4',
        mandarin_audio='[sound:cmn_行_xíng.mp3]',
        cantonese_audio='[sound:yue_行_haang4.mp3]',
    )

    tasks = audio_tasks_for_note(
        note,
        force=True,
        is_valid_audio_tag_fn=lambda tag: True,
    )

    assert tasks == ['mandarin', 'cantonese']


def test_is_valid_audio_tag_uses_passed_audio_directory(tmp_path: Path, monkeypatch) -> None:
    filename = example_audio_filename('你好', 'nǐ hǎo')
    (tmp_path / filename).write_bytes(b'ID3')
    monkeypatch.setattr(audio_files, 'GENERATED_AUDIO_DIR', tmp_path / 'wrong')

    assert is_valid_audio_tag(f'[sound:{filename}]', generated_audio_dir=tmp_path)


def test_preview_mandarin_filename_sanitizes_path_separators() -> None:
    assert preview_mandarin_filename('你/好 test') == 'preview_cmn_你_好_test.mp3'


# -- Sentence audio -----------------------------------------------------------

def test_sentence_audio_filename_is_deterministic() -> None:
    name1 = sentence_audio_filename('水', '我喝水。')
    name2 = sentence_audio_filename('水', '我喝水。')
    assert name1 == name2
    assert name1 == 'cmn_sentence_我喝水。.mp3'


def test_sentence_audio_filename_differs_for_different_sentences() -> None:
    name1 = sentence_audio_filename('水', '我喝水。')
    name2 = sentence_audio_filename('水', '他喝水了。')
    assert name1 != name2


def test_expected_sentence_audio_tag_with_sentence() -> None:
    note = CharacterNote(hanzi='水', keyword='water', sentence='我喝水。')
    tag = expected_sentence_audio_tag(note)
    assert tag == '[sound:cmn_sentence_我喝水。.mp3]'


def test_expected_sentence_audio_tag_empty_without_sentence() -> None:
    note = CharacterNote(hanzi='水', keyword='water')
    assert expected_sentence_audio_tag(note) == ''


def test_audio_tasks_includes_sentence_when_missing() -> None:
    note = CharacterNote(
        hanzi='水',
        keyword='water',
        pinyin='shuǐ',
        jyutping='seoi2',
        mandarin_audio='[sound:cmn_水_shuǐ.mp3]',
        cantonese_audio='[sound:yue_水_seoi2.mp3]',
        sentence='我喝水。',
        # sentence_audio is empty
    )

    tasks = audio_tasks_for_note(
        note,
        force=False,
        is_valid_audio_tag_fn=lambda tag: True,
    )

    assert 'sentence' in tasks
    assert 'mandarin' not in tasks  # already valid


def test_audio_tasks_skips_sentence_when_no_sentence_text() -> None:
    note = CharacterNote(
        hanzi='水',
        keyword='water',
        pinyin='shuǐ',
        jyutping='seoi2',
    )

    tasks = audio_tasks_for_note(
        note,
        force=False,
        is_valid_audio_tag_fn=lambda tag: False,
    )

    assert 'sentence' not in tasks


# -- Orphan audio garbage collection ------------------------------------------

def test_referenced_audio_files_extracts_all_tags() -> None:
    notes = [
        CharacterNote(
            hanzi='水',
            keyword='water',
            mandarin_audio='[sound:cmn_水_shuǐ.mp3]',
            cantonese_audio='[sound:yue_水_seoi2.mp3]',
            example_audio='[sound:cmn_河水_hé_shuǐ.mp3]',
            sentence_audio='[sound:cmn_sentence_我喝水。.mp3]',
        ),
        CharacterNote(
            hanzi='火',
            keyword='fire',
            mandarin_audio='[sound:cmn_火_huǒ.mp3]',
        ),
    ]

    refs = referenced_audio_files(notes)

    assert refs == {
        'cmn_水_shuǐ.mp3',
        'yue_水_seoi2.mp3',
        'cmn_河水_hé_shuǐ.mp3',
        'cmn_sentence_我喝水。.mp3',
        'cmn_火_huǒ.mp3',
    }


def test_referenced_audio_files_ignores_empty_and_invalid_tags() -> None:
    notes = [
        CharacterNote(hanzi='水', keyword='water', mandarin_audio='', example_audio='not-a-tag'),
    ]

    assert referenced_audio_files(notes) == set()


def test_collect_orphaned_audio_finds_unreferenced_files(tmp_path: Path) -> None:
    audio_dir = tmp_path / 'generated'
    audio_dir.mkdir()
    (audio_dir / 'cmn_水_shuǐ.mp3').write_bytes(b'ID3')       # referenced
    (audio_dir / 'cmn_水.mp3').write_bytes(b'ID3')              # orphan (old format)
    (audio_dir / 'cmn_old_word.mp3').write_bytes(b'ID3')        # orphan
    (audio_dir / 'notes.txt').write_text('not audio')           # non-mp3, should be safe

    notes = [
        CharacterNote(hanzi='水', keyword='water', mandarin_audio='[sound:cmn_水_shuǐ.mp3]'),
    ]

    orphans = collect_orphaned_audio(notes, audio_dir)

    orphan_names = {p.name for p in orphans}
    assert orphan_names == {'cmn_水.mp3', 'cmn_old_word.mp3'}
    assert 'notes.txt' not in orphan_names  # non-mp3 untouched


def test_collect_orphaned_audio_returns_empty_when_all_referenced(tmp_path: Path) -> None:
    audio_dir = tmp_path / 'generated'
    audio_dir.mkdir()
    (audio_dir / 'cmn_水_shuǐ.mp3').write_bytes(b'ID3')
    (audio_dir / 'yue_水_seoi2.mp3').write_bytes(b'ID3')

    notes = [
        CharacterNote(
            hanzi='水', keyword='water',
            mandarin_audio='[sound:cmn_水_shuǐ.mp3]',
            cantonese_audio='[sound:yue_水_seoi2.mp3]',
        ),
    ]

    assert collect_orphaned_audio(notes, audio_dir) == []


def test_collect_orphaned_audio_handles_missing_directory(tmp_path: Path) -> None:
    notes = [CharacterNote(hanzi='水', keyword='water')]
    assert collect_orphaned_audio(notes, tmp_path / 'nonexistent') == []


def test_remove_orphaned_audio_deletes_files(tmp_path: Path) -> None:
    audio_dir = tmp_path / 'generated'
    audio_dir.mkdir()
    orphan1 = audio_dir / 'cmn_水.mp3'
    orphan2 = audio_dir / 'cmn_old_stuff.mp3'
    keep = audio_dir / 'cmn_水_shuǐ.mp3'
    orphan1.write_bytes(b'ID3')
    orphan2.write_bytes(b'ID3')
    keep.write_bytes(b'ID3')

    notes = [
        CharacterNote(hanzi='水', keyword='water', mandarin_audio='[sound:cmn_水_shuǐ.mp3]'),
    ]

    removed = remove_orphaned_audio(notes, audio_dir)

    assert len(removed) == 2
    assert not orphan1.exists()
    assert not orphan2.exists()
    assert keep.exists()  # referenced file preserved


def test_remove_orphaned_audio_preserves_non_mp3_files(tmp_path: Path) -> None:
    audio_dir = tmp_path / 'generated'
    audio_dir.mkdir()
    txt = audio_dir / 'readme.txt'
    json_file = audio_dir / 'metadata.json'
    txt.write_text('keep me')
    json_file.write_text('{}')

    notes: list[CharacterNote] = []

    removed = remove_orphaned_audio(notes, audio_dir)

    assert removed == []
    assert txt.exists()
    assert json_file.exists()
