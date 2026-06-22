from io import StringIO

from anki_chinese.cli import AppRuntime, create_app
from anki_chinese.notes import CharacterNote


def _console_output(runtime: AppRuntime) -> str:
    output = runtime.console.file
    assert isinstance(output, StringIO)
    return output.getvalue()


def test_no_args_shows_help_in_non_interactive_context(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "dashboard" in result.output


def test_dashboard_command_refuses_non_interactive_context(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["dashboard"])

    assert result.exit_code == 1
    output = _console_output(runtime)
    assert "requires an interactive terminal" in output
    assert "sync --dry-run" in output
    assert "--json" in output


def test_dashboard_command_can_quit_when_forced(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["dashboard", "--force"], input="q\n")

    assert result.exit_code == 0
    output = _console_output(runtime)
    assert "anki-chinese" in output
    assert "Sync & rebuild" in output
    assert "Goodbye" in output


def test_forced_dashboard_exits_cleanly_when_input_ends(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["dashboard", "--force"], input="")

    assert result.exit_code == 0
    output = _console_output(runtime)
    assert "Input ended; exiting dashboard" in output


def test_dashboard_can_show_sync_plan_then_quit(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["dashboard", "--force"], input="1\nq\n")

    assert result.exit_code == 0
    output = _console_output(runtime)
    assert "Sync plan" in output
    assert "anki-chinese build" in output
    assert "Goodbye" in output


def test_dashboard_song_planner_shows_learn_and_undo_commands(
    runtime_factory,
    runner,
) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["dashboard", "--force"], input="4\nq\n")

    assert result.exit_code == 0
    output = _console_output(runtime)
    assert "Song study planner" in output
    assert "songs learn --limit 20" in output
    assert "songs undo" in output
    assert "Live Anki changes preview by default" in output


def test_dashboard_activation_guidance_mentions_snapshots(
    runtime_factory,
    runner,
) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    result = runner.invoke(app, ["dashboard", "--force"], input="5\nq\n")

    assert result.exit_code == 0
    output = _console_output(runtime)
    assert "Activate / unsuspend in Anki" in output
    assert "activate chars <chars> --dry-run" in output
    assert "activate undo latest" in output
    assert "undo snapshot" in output
