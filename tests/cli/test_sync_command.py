import json

from anki_chinese.cli import create_app
from anki_chinese.cli.sync import run_sync
from anki_chinese.notes import CharacterNote, CharacterSourceStore
from anki_chinese.workflows.pipeline_state import load_pipeline_state


def test_sync_dry_run_json_outputs_machine_readable_plan(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["sync", "--dry-run", "--json"])

    assert result.exit_code == 0
    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    plan = json.loads(output)
    assert plan["dry_run"] is True
    assert plan["required_commands"] == ["anki-chinese build"]
    assert [stage["id"] for stage in plan["stages"]] == ["init", "audio", "build"]
    assert plan["stages"][2]["status"] == "needed"


def test_sync_dry_run_human_output_reports_no_mutation(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])

    run_sync(runtime, dry_run=True)

    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    assert "Sync dry run" in output
    assert "Dry run only. No files changed." in output
    assert not runtime.deck_output_path.exists()


def test_sync_without_dry_run_executes_needed_build(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert runtime.deck_output_path.exists()
    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    assert "Running:" in output
    assert "anki-chinese build" in output
    assert "Sync complete" in output


def test_sync_json_without_dry_run_outputs_machine_readable_result(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["sync", "--json"])

    assert result.exit_code == 0
    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    payload = json.loads(output)
    assert payload["executed_commands"] == ["anki-chinese build"]
    assert payload["plan"]["up_to_date"] is True
    assert "Built" in payload["log"]


def test_sync_executes_init_then_build_when_state_is_missing_and_audio_skipped(
    runtime_factory,
    runner,
) -> None:
    runtime = runtime_factory()
    app = create_app(runtime)

    result = runner.invoke(app, ["sync", "--skip-audio"])

    assert result.exit_code == 0
    assert runtime.note_store.exists()
    assert runtime.deck_output_path.exists()
    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    assert "anki-chinese init" in output
    assert "anki-chinese build" in output


def test_sync_records_canonical_source_for_init(runtime_factory, runner) -> None:
    runtime = runtime_factory()
    runtime.source_records_path = runtime.source_deck_path.parent / "characters.json"
    CharacterSourceStore(runtime.source_records_path).save(
        [CharacterNote(hanzi="一", meaning="one")]
    )
    app = create_app(runtime)

    result = runner.invoke(app, ["sync", "--skip-audio"])

    assert result.exit_code == 0
    state = load_pipeline_state(runtime.pipeline_state_path)
    assert state.stages["init"].inputs["source_deck"].path == str(runtime.source_records_path)


def test_sync_executes_audio_before_build_when_audio_is_pending(
    runtime_factory,
    runner,
    stub_tts_provider,
) -> None:
    runtime = runtime_factory(
        saved_notes=[CharacterNote(hanzi="水", meaning="water", pinyin="shuǐ")],
        tts_provider=stub_tts_provider,
    )
    app = create_app(runtime)

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert stub_tts_provider.calls == [("mandarin", "水", "shuǐ", False)]
    assert runtime.deck_output_path.exists()
    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    assert "anki-chinese audio" in output
    assert "anki-chinese build" in output
