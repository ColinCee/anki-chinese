from pathlib import Path

from anki_chinese.cli.init import _clear_stale_audio, _restore_cached_fields
from anki_chinese.notes import CharacterNote


def test_restore_cached_fields_reuses_valid_audio_example_and_story() -> None:
    current = [CharacterNote(hanzi='行', keyword='go', pinyin='xíng', jyutping='haang4', example_word='银行')]
    previous = [
        CharacterNote(
            hanzi='行',
            keyword='go',
            pinyin='xíng',
            jyutping='haang4',
            mandarin_audio='[sound:cmn_行_xíng.mp3]',
            cantonese_audio='[sound:yue_行_haang4.mp3]',
            example_word='银行',
            example_pinyin='yín háng',
            example_audio='[sound:cmn_银行_yín_háng.mp3]',
            story='walk',
        )
    ]

    _, restored = _restore_cached_fields(
        current,
        previous,
        is_valid_audio_tag=lambda tag: True,
    )

    note = current[0]
    assert restored == 5
    assert note.mandarin_audio == '[sound:cmn_行_xíng.mp3]'
    assert note.cantonese_audio == '[sound:yue_行_haang4.mp3]'
    assert note.example_pinyin == 'yín háng'
    assert note.example_audio == '[sound:cmn_银行_yín_háng.mp3]'
    assert note.story == 'walk'


def test_restore_cached_fields_skips_example_data_when_example_word_changed() -> None:
    current = [CharacterNote(hanzi='行', keyword='go', example_word='行业')]
    previous = [
        CharacterNote(
            hanzi='行',
            keyword='go',
            example_word='银行',
            example_pinyin='yín háng',
            example_audio='[sound:cmn_银行_yín_háng.mp3]',
        )
    ]

    _restore_cached_fields(current, previous, is_valid_audio_tag=lambda tag: True)

    note = current[0]
    assert note.example_pinyin == ''
    assert note.example_audio == ''


def test_clear_stale_audio_removes_files_and_clears_tags(tmp_path: Path) -> None:
    audio_dir = tmp_path / 'generated'
    audio_dir.mkdir()
    for filename in ['cmn_行_old.mp3', 'yue_行_old.mp3', 'cmn_银行_old.mp3']:
        (audio_dir / filename).write_bytes(b'ID3')

    note = CharacterNote(
        hanzi='行',
        keyword='go',
        pinyin='háng',
        jyutping='haang4',
        example_word='银行',
        example_pinyin='yín háng',
        mandarin_audio='[sound:cmn_行_old.mp3]',
        cantonese_audio='[sound:yue_行_old.mp3]',
        example_audio='[sound:cmn_银行_old.mp3]',
    )

    removed = _clear_stale_audio(
        [note],
        generated_audio_dir=audio_dir,
        is_valid_audio_tag=lambda tag: False,
    )

    assert removed == 3
    assert note.mandarin_audio == ''
    assert note.cantonese_audio == ''
    assert note.example_audio == ''
    assert not any(path.exists() for path in audio_dir.iterdir())
