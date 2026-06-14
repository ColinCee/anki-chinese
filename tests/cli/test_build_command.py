from importlib import import_module

from anki_chinese.notes import CharacterNote
from anki_chinese.workflows.pipeline_state import load_pipeline_state

build_module = import_module("anki_chinese.cli.build")


def test_run_build_full_passes_options_through_init_audio_and_build(
    monkeypatch, runtime_factory
) -> None:
    runtime = runtime_factory()
    init_notes = [CharacterNote(hanzi="一", meaning="one", pinyin="yī")]
    audio_notes = [
        CharacterNote(
            hanzi="一", meaning="one", pinyin="yī", mandarin_audio="[sound:cmn_一_yī.mp3]"
        )
    ]
    calls: dict[str, object] = {}

    def fake_init(runtime_arg, input_file):
        calls["init"] = (runtime_arg, input_file)
        return init_notes

    def fake_audio(
        runtime_arg, *, all_notes=None, limit=0, start_rsh=0, force=False, fail_fast=False
    ):
        calls["audio"] = (runtime_arg, all_notes, limit, start_rsh, force, fail_fast)
        return audio_notes

    def fake_build(notes):
        calls["build"] = notes
        output_path = runtime.note_store.path.parent.parent / "build" / "decks" / "deck.apkg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"deck")
        return output_path

    monkeypatch.setattr(build_module, "run_init", fake_init)
    monkeypatch.setattr(build_module, "run_audio", fake_audio)
    runtime.build_deck = fake_build

    result = build_module.run_build(
        runtime,
        full=True,
        audio_limit=3,
        audio_start_rsh=120,
    )

    assert result == runtime.note_store.path.parent.parent / "build" / "decks" / "deck.apkg"
    assert calls["init"] == (runtime, runtime.source_deck_path)
    assert calls["audio"] == (runtime, init_notes, 3, 120, False, False)
    assert calls["build"] == audio_notes


def test_run_build_full_skips_audio_when_requested(monkeypatch, runtime_factory) -> None:
    runtime = runtime_factory()
    init_notes = [CharacterNote(hanzi="一", meaning="one", pinyin="yī")]
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        build_module,
        "run_init",
        lambda runtime_arg, input_file: init_notes,
    )

    def fail_audio(*args, **kwargs):
        raise AssertionError("run_audio should not be called when --skip-audio is set")

    monkeypatch.setattr(build_module, "run_audio", fail_audio)

    def fake_build(notes):
        calls["build"] = notes
        output_path = runtime.note_store.path.parent.parent / "build" / "decks" / "deck.apkg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"deck")
        return output_path

    runtime.build_deck = fake_build

    result = build_module.run_build(runtime, full=True, skip_audio=True)

    assert result == runtime.note_store.path.parent.parent / "build" / "decks" / "deck.apkg"
    assert calls["build"] == init_notes


def test_run_build_records_pipeline_state(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])

    build_module.run_build(runtime)

    state = load_pipeline_state(runtime.pipeline_state_path)
    build_state = state.stages["build"]
    assert build_state.inputs["enriched"].kind == "file"
    assert build_state.outputs["deck"].kind == "file"
