from pathlib import Path

from anki_chinese.cli.init import _clear_stale_audio, _restore_cached_fields
from anki_chinese.notes import CharacterNote


def test_restore_cached_fields_reuses_valid_audio_and_story() -> None:
    current = [CharacterNote(hanzi='行', keyword='go', pinyin='xíng', jyutping='haang4')]
    previous = [
        CharacterNote(
            hanzi='行',
            keyword='go',
            pinyin='xíng',
            jyutping='haang4',
            mandarin_audio='[sound:cmn_行_xíng.mp3]',
            cantonese_audio='[sound:yue_行_haang4.mp3]',
            story='walk',
        )
    ]

    _, restored = _restore_cached_fields(
        current,
        previous,
        is_valid_audio_tag=lambda tag: True,
    )

    note = current[0]
    assert restored == 3
    assert note.mandarin_audio == '[sound:cmn_行_xíng.mp3]'
    assert note.cantonese_audio == '[sound:yue_行_haang4.mp3]'
    assert note.story == 'walk'


def test_clear_stale_audio_removes_files_and_clears_tags(tmp_path: Path) -> None:
    audio_dir = tmp_path / 'generated'
    audio_dir.mkdir()
    for filename in ['cmn_行_old.mp3', 'yue_行_old.mp3']:
        (audio_dir / filename).write_bytes(b'ID3')

    note = CharacterNote(
        hanzi='行',
        keyword='go',
        pinyin='háng',
        jyutping='haang4',
        mandarin_audio='[sound:cmn_行_old.mp3]',
        cantonese_audio='[sound:yue_行_old.mp3]',
    )

    removed = _clear_stale_audio(
        [note],
        generated_audio_dir=audio_dir,
        is_valid_audio_tag=lambda tag: False,
    )

    assert removed == 2
    assert note.mandarin_audio == ''
    assert note.cantonese_audio == ''
    assert not any(path.exists() for path in audio_dir.iterdir())


# -- Sentence-specific init tests ---------------------------------------------

def test_restore_cached_fields_preserves_sentence_fields() -> None:
    # Current note has Heisig keyword from re-parse; previous has Gemini keyword + pinyin
    current = [CharacterNote(hanzi='水', keyword='water', pinyin='shuǐ', sentence='我喝水。')]
    previous = [
        CharacterNote(
            hanzi='水',
            keyword='drink',
            pinyin='hē',
            sentence='我喝水。',
            sentence_pinyin='wǒ hē shuǐ.',
            sentence_english='I drink water.',
            sentence_audio='[sound:cmn_sentence_我喝水。.mp3]',
        )
    ]

    _, restored = _restore_cached_fields(
        current,
        previous,
        is_valid_audio_tag=lambda tag: True,
    )

    note = current[0]
    assert note.keyword == 'drink'  # Gemini keyword preserved over Heisig
    assert note.pinyin == 'hē'  # Gemini pinyin preserved
    assert note.sentence_pinyin == 'wǒ hē shuǐ.'
    assert note.sentence_english == 'I drink water.'
    assert note.sentence_audio == '[sound:cmn_sentence_我喝水。.mp3]'
    assert restored == 5  # sentence_pinyin, sentence_english, sentence_audio, keyword, pinyin


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


def test_restore_keyword_skipped_without_sentence() -> None:
    """Without a sentence, keyword stays as the parsed Heisig value."""
    current = [CharacterNote(hanzi='水', keyword='water')]
    previous = [CharacterNote(hanzi='水', keyword='drink')]

    _restore_cached_fields(
        current,
        previous,
        is_valid_audio_tag=lambda tag: True,
    )

    assert current[0].keyword == 'water'  # no sentence → Heisig kept


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
