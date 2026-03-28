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


# -- Sentence-specific init tests ---------------------------------------------

def test_restore_cached_fields_preserves_sentence_fields() -> None:
    current = [CharacterNote(hanzi='水', keyword='water', sentence='我喝水。')]
    previous = [
        CharacterNote(
            hanzi='水',
            keyword='water',
            sentence='我喝水。',
            sentence_pinyin='wǒ hē shuǐ.',
            sentence_english='I drink water.',
            sentence_keyword='water',
            sentence_audio='[sound:cmn_sentence_我喝水。.mp3]',
        )
    ]

    _, restored = _restore_cached_fields(
        current,
        previous,
        is_valid_audio_tag=lambda tag: True,
    )

    note = current[0]
    assert note.sentence_pinyin == 'wǒ hē shuǐ.'
    assert note.sentence_english == 'I drink water.'
    assert note.sentence_keyword == 'water'
    assert note.sentence_audio == '[sound:cmn_sentence_我喝水。.mp3]'
    assert restored == 4  # pinyin, english, keyword, audio


def test_restore_cached_fields_does_not_overwrite_existing_sentence_data() -> None:
    """If current note already has sentence fields populated, don't clobber them."""
    current = [
        CharacterNote(
            hanzi='水',
            keyword='water',
            sentence='我喝水。',
            sentence_pinyin='new pinyin',
        )
    ]
    previous = [
        CharacterNote(
            hanzi='水',
            keyword='water',
            sentence='我喝水。',
            sentence_pinyin='old pinyin',
            sentence_english='old english',
        )
    ]

    _restore_cached_fields(
        current,
        previous,
        is_valid_audio_tag=lambda tag: True,
    )

    note = current[0]
    assert note.sentence_pinyin == 'new pinyin'  # NOT overwritten
    assert note.sentence_english == 'old english'  # restored (was empty)


def test_clear_stale_audio_removes_sentence_audio_when_invalid(tmp_path: Path) -> None:
    audio_dir = tmp_path / 'generated'
    audio_dir.mkdir()
    (audio_dir / 'cmn_sentence_我喝水。.mp3').write_bytes(b'ID3')

    note = CharacterNote(
        hanzi='水',
        keyword='water',
        sentence='我喝水。',
        sentence_audio='[sound:cmn_sentence_我喝水。.mp3]',
    )

    removed = _clear_stale_audio(
        [note],
        generated_audio_dir=audio_dir,
        is_valid_audio_tag=lambda tag: False,
    )

    assert removed == 1
    assert note.sentence_audio == ''


def test_clear_stale_audio_removes_sentence_audio_when_sentence_changed(tmp_path: Path) -> None:
    """When sentence text changes, the old audio file should be removed."""
    audio_dir = tmp_path / 'generated'
    audio_dir.mkdir()
    old_file = audio_dir / 'cmn_sentence_旧的句子。.mp3'
    old_file.write_bytes(b'ID3')

    note = CharacterNote(
        hanzi='水',
        keyword='water',
        sentence='他喝了很多水。',  # sentence changed
        sentence_audio='[sound:cmn_sentence_旧的句子。.mp3]',  # old tag
    )

    removed = _clear_stale_audio(
        [note],
        generated_audio_dir=audio_dir,
        is_valid_audio_tag=lambda tag: True,
    )

    # Tag doesn't match expected for new sentence → cleared
    assert removed == 1
    assert note.sentence_audio == ''
    assert not old_file.exists()
