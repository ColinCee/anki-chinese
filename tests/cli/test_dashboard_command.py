import textwrap
from io import StringIO
from typing import cast
from unittest.mock import patch

import pytest
from textual.widgets import Input, Static

from anki_chinese.cli import AppRuntime, create_app
from anki_chinese.notes import CharacterNote
from anki_chinese.tui.dashboard import DashboardApp
from anki_chinese.tui.dashboard_model import recommend_workflow
from anki_chinese.workflows.sync import SyncPlan, SyncStagePlan


def _content(app: DashboardApp, selector: str) -> str:
    return str(cast(Static, app.query_one(selector)).content)


def _input(app: DashboardApp, selector: str) -> Input:
    return cast(Input, app.query_one(selector))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _console_output(runtime: AppRuntime) -> str:
    output = runtime.console.file
    assert isinstance(output, StringIO)
    return output.getvalue()


class StubSongKnowledgeClient:
    def find_active_characters(self) -> set[str]:
        return {"一"}

    def find_studied_characters(self) -> set[str]:
        return {"一"}

    def find_all_deck_info(self) -> tuple[list[str], set[str]]:
        deck_order = ["一", "二", "三", "四"]
        return deck_order, set(deck_order)


def _write_dashboard_song(runtime: AppRuntime, *, title: str, body: str, file_name: str) -> None:
    runtime.song_lyrics_dir.mkdir(parents=True, exist_ok=True)
    (runtime.song_lyrics_dir / file_name).write_text(
        textwrap.dedent("""\
            ---
            title: {title}
            artist: 测试
            ---
            {body}
        """).format(title=title, body=body),
        encoding="utf-8",
    )


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
        assert "Recommended:" in _content(app, "#summary")
        assert "Primary action:" in _content(app, "#summary")
        assert "Preview sync plan" in _content(app, "#primary-action")
        assert "Recommended" in _content(app, "#workflow-1 Label")
        assert app.query_one("#menu-view").display is True
        assert app.query_one("#detail-view").display is False
        assert "Other workflows" in _content(app, "#menu-help")
        assert "Inspect cards" not in _content(app, "#workflow-2 Label")
        await pilot.press("enter")
        assert "Preview: Rebuild deck" in _content(app, "#detail-title")
        assert "Sync plan" in _content(app, "#sync-stages")
        assert "Reason:" in _content(app, "#sync-stages")
        assert "uv run anki-chinese sync --dry-run" in _content(app, "#commands")


@pytest.mark.anyio
async def test_textual_dashboard_runs_sync_action(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = DashboardApp(runtime)

    async with app.run_test(size=(70, 28)) as pilot:
        await pilot.press("x")
        assert "Run: Rebuild deck" in _content(app, "#detail-title")
        assert "Sync output" in _content(app, "#action-output")
        assert "Sync complete" in _content(app, "#action-output")
        assert runtime.deck_output_path.is_file()
        assert "No live Anki state was changed" in _content(app, "#safety")


def test_dashboard_recommendation_prefers_review_after_sync_is_current(runtime_factory) -> None:
    runtime = runtime_factory(
        saved_notes=[
            CharacterNote(
                hanzi="行",
                meaning="go",
                pinyin="xíng",
                needs_review=True,
                review_reason="Check reading",
            )
        ]
    )
    current_plan = SyncPlan(
        stages=[
            SyncStagePlan(
                id="init",
                label="Parse + enrich",
                status="up_to_date",
                reason="current",
                command="anki-chinese init",
            ),
        ]
    )

    recommendation = recommend_workflow(runtime, current_plan)

    assert recommendation.workflow_key == "2"
    assert recommendation.title == "Improve cards"


@pytest.mark.anyio
async def test_textual_dashboard_song_guidance(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = DashboardApp(runtime)

    async with app.run_test(size=(50, 24)) as pilot:
        await pilot.press("down", "down", "down", "enter")
        assert "Learn songs" in _content(app, "#detail-title")
        assert "songs learn --limit 20" in _content(app, "#commands")
        assert "songs undo" in _content(app, "#commands")
        assert "Live Anki changes preview by default" in _content(app, "#safety")
        assert app.query_one("#menu-view").display is False
        assert app.query_one("#detail-view").display is True
        await pilot.press("escape")
        assert app.query_one("#menu-view").display is True
        assert app.query_one("#detail-view").display is False


@pytest.mark.anyio
async def test_textual_dashboard_runs_content_audio_inspection(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = DashboardApp(runtime)

    async with app.run_test(size=(70, 28)) as pilot:
        await pilot.press("down", "down", "x")
        assert "Inspect: Generate content/audio" in _content(app, "#detail-title")
        assert "Content/audio state" in _content(app, "#action-output")
        assert "Notes needing audio updates" in _content(app, "#action-output")
        assert "No Gemini, TTS, or live Anki action was run" in _content(app, "#safety")


@pytest.mark.anyio
async def test_textual_dashboard_runs_song_preview_without_activation(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    _write_dashboard_song(runtime, title="已会", body="一", file_name="01-known.md")
    _write_dashboard_song(runtime, title="测试歌", body="一二三喵", file_name="02-next.md")
    app = DashboardApp(runtime)

    async with app.run_test(size=(80, 32)) as pilot:
        await pilot.press("down", "down", "down", "enter")
        _input(app, "#song-query").value = "测试歌"
        with patch("anki_chinese.tui.dashboard.AnkiConnectClient", return_value=StubSongKnowledgeClient()):
            await pilot.press("x")

        assert "Recommended next song" in _content(app, "#action-output")
        assert "测试歌" in _content(app, "#action-output")
        assert "Chars: 二 三" in _content(app, "#action-output")
        assert "All songs" in _content(app, "#action-output")
        assert "does not activate cards" in _content(app, "#safety")


@pytest.mark.anyio
async def test_textual_dashboard_card_editor_loads_and_saves_source_edit(runtime_factory) -> None:
    runtime = runtime_factory(
        saved_notes=[
            CharacterNote(
                hanzi="水",
                meaning="water",
                sentence="我喝水。",
                sentence_pinyin="wǒ hē shuǐ.",
                sentence_english="I drink water.",
                sentence_audio="[sound:old.mp3]",
            )
        ]
    )
    app = DashboardApp(runtime)

    async with app.run_test(size=(80, 32)) as pilot:
        await pilot.press("down", "enter")
        _input(app, "#card-hanzi").value = "水"
        await pilot.press("l")
        assert _input(app, "#card-meaning").value == "water"
        assert "Loaded card" in _content(app, "#action-output")

        _input(app, "#card-meaning").value = "water; liquid"
        _input(app, "#card-sentence").value = "我喜欢喝水。"
        _input(app, "#card-sentence-pinyin").value = "wǒ xǐ huān hē shuǐ."
        _input(app, "#card-sentence-english").value = "I like drinking water."
        await pilot.press("s")

        assert "Saved source deck edit" in _content(app, "#action-output")
        assert "No live Anki state was changed" in _content(app, "#safety")

    [note] = runtime.note_store.load()
    assert note.meaning == "water; liquid"
    assert note.sentence == "我喜欢喝水。"
    assert note.sentence_pinyin == "wǒ xǐ huān hē shuǐ."
    assert note.sentence_english == "I like drinking water."
    assert note.sentence_audio == ""


@pytest.mark.anyio
async def test_textual_dashboard_health_guidance_includes_doctor(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = DashboardApp(runtime)

    async with app.run_test(size=(50, 24)) as pilot:
        await pilot.press("down", "down", "down", "down", "enter")
        assert "Health, cleanup, undo" in _content(app, "#detail-title")
        assert "doctor" in _content(app, "#commands")


@pytest.mark.anyio
async def test_textual_dashboard_runs_health_action(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = DashboardApp(runtime)

    async with app.run_test(size=(70, 28)) as pilot:
        await pilot.press("down", "down", "down", "down", "x")
        assert "Run: Health, cleanup, undo" in _content(app, "#detail-title")
        assert "Doctor output" in _content(app, "#action-output")
        assert "Source deck export" in _content(app, "#action-output")
        assert "Recent snapshots" in _content(app, "#action-output")
        assert "No live Anki state was changed" in _content(app, "#safety")


@pytest.mark.anyio
async def test_textual_dashboard_health_guidance_includes_activation_recovery(runtime_factory) -> None:
    runtime = runtime_factory(saved_notes=[CharacterNote(hanzi="一", meaning="one")])
    app = DashboardApp(runtime)

    async with app.run_test(size=(50, 24)) as pilot:
        await pilot.press("down", "down", "down", "down", "enter")
        assert "Health, cleanup, undo" in _content(app, "#detail-title")
        assert "activate chars <chars> --dry-run" in _content(app, "#commands")
        assert "activate undo latest" in _content(app, "#commands")
        assert "undo snapshots" in _content(app, "#safety")
