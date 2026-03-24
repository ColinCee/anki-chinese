import pytest
import typer

from anki_chinese.cli.audio import run_audio
from anki_chinese.notes import CharacterNote


def test_run_audio_saves_completed_work_before_rate_limit(runtime_factory, stub_tts_provider) -> None:
    stub_tts_provider.rate_limit_on.add('mandarin:二')
    notes = [
        CharacterNote(hanzi='一', keyword='one', pinyin='yī'),
        CharacterNote(hanzi='二', keyword='two', pinyin='èr'),
    ]
    runtime = runtime_factory(saved_notes=notes, tts_provider=stub_tts_provider)

    with pytest.raises(typer.Exit) as exc_info:
        run_audio(runtime)

    assert exc_info.value.exit_code == 2
    saved = runtime.note_store.load()
    assert saved[0].mandarin_audio == '[sound:cmn_一_yī.mp3]'
    assert saved[1].mandarin_audio == ''
