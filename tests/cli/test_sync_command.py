import json

from anki_chinese.cli import create_app
from anki_chinese.cli.sync import run_sync
from anki_chinese.notes import CharacterNote


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


def test_sync_without_dry_run_refuses_execution_for_now(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    assert "Sync execution is not implemented yet" in output


def test_sync_json_without_dry_run_outputs_machine_readable_error(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["sync", "--json"])

    assert result.exit_code == 1
    output = runtime.console.file.getvalue()  # type: ignore[union-attr]
    payload = json.loads(output)
    assert "not implemented yet" in payload["error"]
    assert payload["plan"]["stages"][2]["id"] == "build"
