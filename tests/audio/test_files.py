from pathlib import Path

import anki_chinese.audio.files as audio_files
from anki_chinese.audio.files import (
    audio_tasks_for_note,
    example_audio_filename,
    expected_cantonese_audio_tag,
    expected_example_audio_tag,
    expected_mandarin_audio_tag,
    is_valid_audio_tag,
    preview_mandarin_filename,
)
from anki_chinese.notes import CharacterNote


def test_expected_audio_tags_are_empty_when_required_fields_are_missing() -> None:
    note = CharacterNote(hanzi='一', keyword='one')

    assert expected_mandarin_audio_tag(note) == ''
    assert expected_cantonese_audio_tag(note) == ''
    assert expected_example_audio_tag(note) == ''


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
