import pytest
import typer

from anki_chinese.cli.audio import run_audio, run_audio_clean
from anki_chinese.notes import CharacterNote
from anki_chinese.workflows.pipeline_state import load_pipeline_state


def test_run_audio_filters_by_character(runtime_factory, stub_tts_provider) -> None:
    notes = [
        CharacterNote(hanzi="一", meaning="one", pinyin="yī"),
        CharacterNote(hanzi="二", meaning="two", pinyin="èr"),
    ]
    runtime = runtime_factory(saved_notes=notes, tts_provider=stub_tts_provider)

    run_audio(runtime, char="二")

    saved = runtime.note_store.load()
    assert saved[0].mandarin_audio == ""
    assert saved[1].mandarin_audio == "[sound:cmn_二_èr.mp3]"
    assert stub_tts_provider.calls == [("mandarin", "二", "èr", False)]


def test_run_audio_records_pipeline_state(runtime_factory, stub_tts_provider) -> None:
    runtime = runtime_factory(
        saved_notes=[CharacterNote(hanzi="一", meaning="one", pinyin="yī")],
        tts_provider=stub_tts_provider,
    )

    run_audio(runtime)

    state = load_pipeline_state(runtime.pipeline_state_path)
    audio_state = state.stages["audio"]
    assert audio_state.inputs["enriched"].kind == "file"
    assert audio_state.outputs["generated_audio"].kind in {"directory", "missing"}


def test_run_audio_applies_start_rsh_and_limit(runtime_factory, stub_tts_provider) -> None:
    notes = [
        CharacterNote(hanzi="一", meaning="one", pinyin="yī", heisig_num="RSH 1"),
        CharacterNote(hanzi="二", meaning="two", pinyin="èr", heisig_num="RSH 2"),
        CharacterNote(hanzi="三", meaning="three", pinyin="sān", heisig_num="RSH 3"),
    ]
    runtime = runtime_factory(saved_notes=notes, tts_provider=stub_tts_provider)

    run_audio(runtime, start_rsh=2, limit=1)

    assert stub_tts_provider.calls == [("mandarin", "二", "èr", False)]


def test_run_audio_exits_when_requested_character_is_missing(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one", pinyin="yī")])

    with pytest.raises(typer.Exit) as exc_info:
        run_audio(runtime, char="三")

    assert exc_info.value.exit_code == 1


def test_run_audio_clean_reports_orphans_without_deleting(runtime_factory) -> None:
    note = CharacterNote(hanzi="水", sentence_audio="[sound:cmn_sentence_我喝水。.mp3]")
    runtime = runtime_factory(saved_notes=[note])
    runtime.generated_audio_dir.mkdir(parents=True)
    kept = runtime.generated_audio_dir / "cmn_sentence_我喝水。.mp3"
    orphan = runtime.generated_audio_dir / "cmn_sentence_old.mp3"
    kept.write_bytes(b"ID3")
    orphan.write_bytes(b"ID3")

    removed = run_audio_clean(runtime)

    assert removed == ["cmn_sentence_old.mp3"]
    assert orphan.exists()
    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    assert "Dry run" in output


def test_run_audio_clean_deletes_orphans_when_applied(runtime_factory) -> None:
    note = CharacterNote(hanzi="水", sentence_audio="[sound:cmn_sentence_我喝水。.mp3]")
    runtime = runtime_factory(saved_notes=[note])
    runtime.generated_audio_dir.mkdir(parents=True)
    kept = runtime.generated_audio_dir / "cmn_sentence_我喝水。.mp3"
    orphan = runtime.generated_audio_dir / "cmn_sentence_old.mp3"
    kept.write_bytes(b"ID3")
    orphan.write_bytes(b"ID3")

    removed = run_audio_clean(runtime, apply=True)

    assert removed == ["cmn_sentence_old.mp3"]
    assert kept.exists()
    assert not orphan.exists()


def test_run_audio_clean_can_filter_to_sentence_orphans(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="水")])
    runtime.generated_audio_dir.mkdir(parents=True)
    sentence_orphan = runtime.generated_audio_dir / "cmn_sentence_old.mp3"
    mandarin_orphan = runtime.generated_audio_dir / "cmn_旧_jiù.mp3"
    sentence_orphan.write_bytes(b"ID3")
    mandarin_orphan.write_bytes(b"ID3")

    removed = run_audio_clean(runtime, apply=True, kind="sentence")

    assert removed == ["cmn_sentence_old.mp3"]
    assert not sentence_orphan.exists()
    assert mandarin_orphan.exists()
