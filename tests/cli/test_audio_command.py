import pytest
import typer

from anki_chinese.cli.audio import run_audio
from anki_chinese.notes import CharacterNote


def test_run_audio_filters_by_character(runtime_factory, stub_tts_provider) -> None:
    notes = [
        CharacterNote(hanzi='一', meaning='one', pinyin='yī'),
        CharacterNote(hanzi='二', meaning='two', pinyin='èr'),
    ]
    runtime = runtime_factory(saved_notes=notes, tts_provider=stub_tts_provider)

    run_audio(runtime, char='二')

    saved = runtime.note_store.load()
    assert saved[0].mandarin_audio == ''
    assert saved[1].mandarin_audio == '[sound:cmn_二_èr.mp3]'
    assert stub_tts_provider.calls == [('mandarin', '二', 'èr', False)]


def test_run_audio_applies_start_rsh_and_limit(runtime_factory, stub_tts_provider) -> None:
    notes = [
        CharacterNote(hanzi='一', meaning='one', pinyin='yī', heisig_num='RSH 1'),
        CharacterNote(hanzi='二', meaning='two', pinyin='èr', heisig_num='RSH 2'),
        CharacterNote(hanzi='三', meaning='three', pinyin='sān', heisig_num='RSH 3'),
    ]
    runtime = runtime_factory(saved_notes=notes, tts_provider=stub_tts_provider)

    run_audio(runtime, start_rsh=2, limit=1)

    assert stub_tts_provider.calls == [('mandarin', '二', 'èr', False)]


def test_run_audio_exits_when_requested_character_is_missing(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi='一', meaning='one', pinyin='yī')])

    with pytest.raises(typer.Exit) as exc_info:
        run_audio(runtime, char='三')

    assert exc_info.value.exit_code == 1
