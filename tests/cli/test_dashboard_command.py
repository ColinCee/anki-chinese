from io import StringIO
from unittest.mock import patch

import pytest

from anki_chinese.cli import AppRuntime, create_app
from anki_chinese.notes import CharacterNote
from anki_chinese.tui.dashboard import DashboardApp


def _content(app: DashboardApp, selector: str) -> str:
    return str(app.query_one(selector).content)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


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


def test_dashboard_command_runs_textual_app_when_forced(runtime_factory, runner) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = create_app(runtime)

    with patch("anki_chinese.cli.dashboard.run_dashboard") as run_dashboard:
        result = runner.invoke(app, ["dashboard", "--force"])

    assert result.exit_code == 0
    run_dashboard.assert_called_once_with(runtime)


@pytest.mark.anyio
async def test_textual_dashboard_renders_sync_plan(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = DashboardApp(runtime)

    async with app.run_test(size=(50, 24)) as pilot:
        await pilot.pause()
        assert "anki-chinese" in _content(app, "#summary")
        assert app.query_one("#menu-view").display is True
        assert app.query_one("#detail-view").display is False
        assert "Choose a workflow" in _content(app, "#menu-help")
        assert "Inspect cards" not in _content(app, "#workflow-2 Label")
        await pilot.press("enter")
        assert "Sync & rebuild" in _content(app, "#detail-title")
        assert "Sync plan" in _content(app, "#sync-stages")
        assert "Reason:" in _content(app, "#sync-stages")
        assert "anki-chinese build" in _content(app, "#commands")


@pytest.mark.anyio
async def test_textual_dashboard_song_guidance(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = DashboardApp(runtime)

    async with app.run_test(size=(50, 24)) as pilot:
        await pilot.press("down", "down", "down", "enter")
        assert "Song study planner" in _content(app, "#detail-title")
        assert "songs learn --limit 20" in _content(app, "#commands")
        assert "songs undo" in _content(app, "#commands")
        assert "Live Anki changes preview by default" in _content(app, "#safety")
        assert app.query_one("#menu-view").display is False
        assert app.query_one("#detail-view").display is True
        await pilot.press("escape")
        assert app.query_one("#menu-view").display is True
        assert app.query_one("#detail-view").display is False


@pytest.mark.anyio
async def test_textual_dashboard_activation_guidance(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = DashboardApp(runtime)

    async with app.run_test(size=(50, 24)) as pilot:
        await pilot.press("down", "down", "down", "down", "enter")
        assert "Activate / unsuspend in Anki" in _content(app, "#detail-title")
        assert "activate chars <chars> --dry-run" in _content(app, "#commands")
        assert "activate undo latest" in _content(app, "#commands")
        assert "undo snapshot" in _content(app, "#safety")
