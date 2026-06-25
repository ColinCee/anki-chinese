"""Textual dashboard for human workflows."""

from __future__ import annotations

import json
from collections.abc import Callable
from io import StringIO
from typing import cast

import typer
from rich.console import Console
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from ..audio.state import audio_generation_profiles, build_audio_deck_state, load_audio_manifest
from ..notes import CharacterNote, flagged_notes, validation_issues
from ..workflows.sync import SyncPlan
from .dashboard_model import (
    WORKFLOW_ITEMS,
    DashboardRuntime,
    WorkflowItem,
    current_sync_plan,
    recommend_workflow,
    sync_summary,
)


class DashboardApp(App[None]):
    """Terminal app that guides humans through the main workflows."""

    CSS = """
    Screen {
        background: $surface;
    }

    #summary {
        dock: top;
        height: 8;
        padding: 1 2;
        background: $panel;
        border: round $primary;
    }

    #body, #menu-view, #detail-view {
        height: 1fr;
        width: 1fr;
    }

    #menu-view, #detail-view {
        border: round $primary;
        margin: 1;
        padding: 1 2;
    }

    #primary-action {
        border: round $success;
        padding: 1 2;
        margin-bottom: 1;
    }

    #workflow-list {
        height: 1fr;
    }

    #menu-help {
        color: $text-muted;
        margin-bottom: 1;
    }

    #detail-scroll {
        height: 1fr;
    }

    #detail-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #detail-body {
        height: auto;
        margin-bottom: 1;
    }

    #commands {
        height: auto;
        margin-bottom: 1;
    }

    #action-output {
        height: auto;
        margin-bottom: 1;
        border: round $accent;
        padding: 1 2;
    }

    #card-editor, #song-planner {
        height: auto;
        margin-bottom: 1;
        border: round $primary;
        padding: 1 2;
    }

    #safety {
        color: $warning;
    }

    #sync-stages {
        margin-top: 1;
        margin-bottom: 1;
    }

    #back-hint {
        dock: bottom;
        color: $text-muted;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "go_back", "Back"),
        ("p", "preview_recommendation", "Preview"),
        ("x", "run_selected", "Run"),
        ("l", "load_card", "Load card"),
        ("s", "save_card", "Save card"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, runtime: DashboardRuntime) -> None:
        super().__init__()
        self.runtime = runtime
        self.plan: SyncPlan | None = None
        self.items = WORKFLOW_ITEMS
        self.current_index = 0
        self.recommended_key = "1"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="summary")
        with Vertical(id="body"):
            with Vertical(id="menu-view"):
                yield Label("Dashboard cockpit", id="workflow-heading")
                yield Static("", id="primary-action")
                yield Static("Other workflows: choose one, then press Enter for details.", id="menu-help")
                yield ListView(
                    *[
                        ListItem(
                            Label(f"{item.key}. {item.label}"),
                            id=f"workflow-{item.key}",
                        )
                        for item in self.items
                    ],
                    id="workflow-list",
                )
            with Vertical(id="detail-view"):
                with VerticalScroll(id="detail-scroll"):
                    yield Static("", id="detail-title")
                    yield Static("", id="detail-body")
                    yield Static("", id="sync-stages")
                    yield Static("", id="action-output")
                    with Vertical(id="card-editor"):
                        yield Static("[bold]Card editor[/bold]\nEnter a character, press l to load, edit fields, press s to save.")
                        yield Input(placeholder="Character", id="card-hanzi", max_length=4)
                        yield Input(placeholder="Meaning", id="card-meaning")
                        yield Input(placeholder="Sentence", id="card-sentence")
                        yield Input(placeholder="Sentence pinyin", id="card-sentence-pinyin")
                        yield Input(placeholder="Sentence English", id="card-sentence-english")
                    with Vertical(id="song-planner"):
                        yield Static(
                            "[bold]Song planner[/bold]\n"
                            "Optionally enter a song title, then press x to preview the next batch. "
                            "This does not activate cards."
                        )
                        yield Input(placeholder="Song title or blank for next recommended song", id="song-query")
                    yield Static("", id="commands")
                    yield Static("", id="safety")
                yield Static("p: preview · x: run safe action · Esc: back · r: refresh · q: quit", id="back-hint")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "anki-chinese"
        self.sub_title = "workflow dashboard"
        self._refresh_plan()
        self._show_menu()

    def action_refresh(self) -> None:
        self._refresh_plan()
        detail_view = self.query_one("#detail-view", Vertical)
        if detail_view.display:
            self._show_workflow(self.items[self.current_index])

    def action_preview_recommendation(self) -> None:
        self._preview_recommended_action()

    def action_run_selected(self) -> None:
        self._run_workflow_action(self._active_item())

    def action_load_card(self) -> None:
        if self._active_item().key == "2":
            self._load_card_editor()

    def action_save_card(self) -> None:
        if self._active_item().key == "2":
            self._save_card_editor()

    def action_go_back(self) -> None:
        self._show_menu()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.current_index = event.index
        item = self.items[event.index]
        if item.key == self.recommended_key:
            self._preview_workflow(item)
            return
        self._show_workflow(item)

    def _refresh_plan(self) -> None:
        self.plan = current_sync_plan(self.runtime)
        recommendation = recommend_workflow(self.runtime, self.plan)
        summary = self.query_one("#summary", Static)
        summary.update(
            "\n".join(
                [
                    "[bold]anki-chinese[/bold]",
                    f"Sync: [cyan]{sync_summary(self.plan)}[/cyan]",
                    f"Recommended: [bold]{recommendation.title}[/bold]",
                    f"Why: {recommendation.reason}",
                    f"Primary action: [bold]{self.items[self._item_index(recommendation.workflow_key)].primary_action}[/bold]",
                    f"Command equivalent: [bold]{self._primary_command_equivalent(recommendation.workflow_key)}[/bold]",
                ]
            )
        )
        self.recommended_key = recommendation.workflow_key
        self.current_index = self._item_index(self.recommended_key)
        self._refresh_menu_labels()
        self._refresh_primary_action(recommendation.title, recommendation.reason)

    def _item_index(self, key: str) -> int:
        return next((index for index, item in enumerate(self.items) if item.key == key), 0)

    def _active_item(self) -> WorkflowItem:
        menu_view = self.query_one("#menu-view", Vertical)
        if menu_view.display:
            workflow_list = self.query_one("#workflow-list", ListView)
            if workflow_list.index is not None:
                self.current_index = workflow_list.index
        return self.items[self.current_index]

    def _refresh_menu_labels(self) -> None:
        for item in self.items:
            label = self.query_one(f"#workflow-{item.key} Label", Label)
            suffix = "  [green]Recommended[/green]" if item.key == self.recommended_key else ""
            label.update(f"{item.key}. {item.label}{suffix}")

    def _primary_command_equivalent(self, workflow_key: str) -> str:
        if workflow_key == "1":
            return "uv run anki-chinese sync --dry-run"
        item = self.items[self._item_index(workflow_key)]
        return item.commands[0] if item.commands else "No command equivalent"

    def _refresh_primary_action(self, title: str, reason: str) -> None:
        item = self.items[self._item_index(self.recommended_key)]
        self.query_one("#primary-action", Static).update(
            "\n".join(
                [
                    f"[bold]Recommended:[/bold] {title}",
                    f"[bold]Why:[/bold] {reason}",
                    f"[bold]Action:[/bold] {item.primary_action}",
                    "[dim]Press p to preview, x to run safe actions, or Enter on a row for details.[/dim]",
                ]
            )
        )

    def _show_workflow(self, item: WorkflowItem) -> None:
        self.query_one("#menu-view", Vertical).display = False
        self.query_one("#detail-view", Vertical).display = True
        self.query_one("#detail-title", Static).update(item.label)
        self.query_one("#detail-body", Static).update(item.detail)
        self._render_sync_stages(show=item.key == "1")
        self._clear_action_output()
        self._render_card_editor(show=item.key == "2")
        self._render_song_planner(show=item.key == "4")
        self._render_commands(item)
        safety = f"Safety: {item.safety}" if item.safety else ""
        self.query_one("#safety", Static).update(safety)

    def _preview_recommended_action(self) -> None:
        self._preview_workflow(self.items[self._item_index(self.recommended_key)])

    def _preview_workflow(self, item: WorkflowItem) -> None:
        self.query_one("#menu-view", Vertical).display = False
        self.query_one("#detail-view", Vertical).display = True
        self.query_one("#detail-title", Static).update(f"Preview: {item.label}")
        self.query_one("#detail-body", Static).update(self._preview_body(item))
        self._render_sync_stages(show=item.key == "1")
        self._render_preview_action_hint(item)
        self._render_card_editor(show=item.key == "2")
        self._render_song_planner(show=item.key == "4")
        self._render_commands(item, preview=True)
        safety = f"Safety: {item.safety}" if item.safety else "Preview only. No files or live Anki state changed."
        self.query_one("#safety", Static).update(safety)

    def _show_menu(self) -> None:
        self.query_one("#menu-view", Vertical).display = True
        self.query_one("#detail-view", Vertical).display = False
        workflow_list = self.query_one("#workflow-list", ListView)
        workflow_list.index = self.current_index
        workflow_list.focus()

    def _render_sync_stages(self, *, show: bool) -> None:
        sync_stages = self.query_one("#sync-stages", Static)
        if not show:
            sync_stages.display = False
            return

        sync_stages.display = True
        if self.plan is None:
            self._refresh_plan()
        assert self.plan is not None
        lines = ["[bold]Sync plan[/bold]"]
        for stage in self.plan.stages:
            lines.extend(
                [
                    "",
                    f"[cyan]{stage.label}[/cyan]",
                    f"  Status: {stage.status}",
                    f"  Reason: {stage.reason}",
                ]
            )
        sync_stages.update("\n".join(lines))

    def _clear_action_output(self) -> None:
        action_output = self.query_one("#action-output", Static)
        action_output.display = False
        action_output.update("")

    def _render_card_editor(self, *, show: bool) -> None:
        editor = self.query_one("#card-editor", Vertical)
        editor.display = show

    def _render_song_planner(self, *, show: bool) -> None:
        planner = self.query_one("#song-planner", Vertical)
        planner.display = show

    def _render_preview_action_hint(self, item: WorkflowItem) -> None:
        action_output = self.query_one("#action-output", Static)
        action_output.display = True
        if item.key == "1":
            action_output.update("[bold]Ready:[/bold] Press x to run `uv run anki-chinese sync` in-place.")
            return
        if item.key == "5":
            action_output.update(
                "[bold]Ready:[/bold] Press x to run read-only doctor checks in-place. "
                "This does not probe AnkiConnect."
            )
            return
        if item.key == "4":
            action_output.update(
                "[bold]Ready:[/bold] Press x to preview the next song batch. "
                "This queries local AnkiConnect state but does not activate cards."
            )
            return
        if item.key == "3":
            action_output.update("[bold]Ready:[/bold] Press x to inspect generated content and audio state.")
            return
        action_output.update("[dim]No in-place run action yet for this workflow; use the command equivalents below.[/dim]")

    def _capture_runtime_output(self, action: Callable[[], object]) -> str:
        original_console = self.runtime.console
        buffer = StringIO()
        self.runtime.console = Console(file=buffer, force_terminal=False, color_system=None, width=100)
        try:
            action()
        except typer.Exit as error:
            output = buffer.getvalue().rstrip()
            code = error.exit_code if error.exit_code is not None else 0
            suffix = f"Exited with code {code}."
            return f"{output}\n{suffix}" if output else suffix
        finally:
            self.runtime.console = original_console
        return buffer.getvalue().rstrip() or "Completed."

    def _run_workflow_action(self, item: WorkflowItem) -> None:
        if item.key == "1":
            self._run_sync_action()
            return
        if item.key == "5":
            self._run_health_action()
            return
        if item.key == "4":
            self._run_song_preview_action()
            return
        if item.key == "3":
            self._run_content_audio_action()
            return

        action_output = self.query_one("#action-output", Static)
        action_output.display = True
        action_output.update(
            "[yellow]No safe in-place action is wired for this workflow yet.[/yellow]\n"
            "Use the command equivalents for now."
        )

    def _run_sync_action(self) -> None:
        from ..cli.app import AppRuntime
        from ..cli.sync import run_sync

        self.query_one("#menu-view", Vertical).display = False
        self.query_one("#detail-view", Vertical).display = True
        self.query_one("#detail-title", Static).update("Run: Rebuild deck")
        self.query_one("#detail-body", Static).update("Running `uv run anki-chinese sync` in-place.")
        action_output = self.query_one("#action-output", Static)
        action_output.display = True
        action_output.update("[bold]Running sync...[/bold]")

        output = self._capture_runtime_output(
            lambda: run_sync(cast(AppRuntime, self.runtime), dry_run=False, json_output=False)
        )
        self._refresh_plan()
        self._render_sync_stages(show=True)
        self._render_commands(self.items[self._item_index("1")], preview=True)
        action_output.update("\n".join(["[bold]Sync output[/bold]", output]))
        self.query_one("#safety", Static).update("No live Anki state was changed.")

    def _run_health_action(self) -> None:
        from ..activation import list_activation_snapshots
        from ..cli.app import AppRuntime
        from ..cli.doctor import run_doctor
        from ..config import ANKI_BACKUP_DIR

        self.query_one("#menu-view", Vertical).display = False
        self.query_one("#detail-view", Vertical).display = True
        self.query_one("#detail-title", Static).update("Run: Health, cleanup, undo")
        self.query_one("#detail-body", Static).update("Running read-only doctor checks without AnkiConnect probing.")
        self._render_sync_stages(show=False)
        action_output = self.query_one("#action-output", Static)
        action_output.display = True
        action_output.update("[bold]Running doctor...[/bold]")

        output = self._capture_runtime_output(
            lambda: run_doctor(cast(AppRuntime, self.runtime), check_anki=False, strict=False)
        )
        snapshots = list_activation_snapshots(ANKI_BACKUP_DIR, limit=5)
        snapshot_lines = ["", "[bold]Recent snapshots[/bold]"]
        if snapshots:
            snapshot_lines.extend(
                f"{snapshot.path.name}: {snapshot.operation}, {snapshot.mutation_card_count} cards, {snapshot.note_count} notes"
                for snapshot in snapshots
            )
        else:
            snapshot_lines.append("No activation snapshots found.")
        self._refresh_plan()
        self._render_commands(self.items[self._item_index("5")], preview=True)
        action_output.update("\n".join(["[bold]Doctor output[/bold]", output, *snapshot_lines]))
        self.query_one("#safety", Static).update("Read-only. No live Anki state was changed.")

    def _run_song_preview_action(self) -> None:
        from ..cli.app import AppRuntime
        from ..cli.songs import run_songs_next

        song_query = self._card_input_value("#song-query")
        self.query_one("#menu-view", Vertical).display = False
        self.query_one("#detail-view", Vertical).display = True
        self.query_one("#detail-title", Static).update("Preview: Learn songs")
        self.query_one("#detail-body", Static).update(
            "Previewing the next song-learning batch. This does not activate cards."
        )
        self._render_sync_stages(show=False)
        self._render_song_planner(show=True)
        action_output = self.query_one("#action-output", Static)
        action_output.display = True
        action_output.update("[bold]Planning song batch...[/bold]")

        output = self._capture_runtime_output(
            lambda: run_songs_next(
                cast(AppRuntime, self.runtime),
                song_query,
                lyrics_dir=self.runtime.song_lyrics_dir,
                limit=20,
            )
        )
        self._render_commands(self.items[self._item_index("4")], preview=True)
        action_output.update("\n".join(["[bold]Song preview output[/bold]", output]))
        self.query_one("#safety", Static).update(
            "Preview only. No cards were activated and no live Anki state was changed."
        )

    def _run_content_audio_action(self) -> None:
        self.query_one("#menu-view", Vertical).display = False
        self.query_one("#detail-view", Vertical).display = True
        self.query_one("#detail-title", Static).update("Inspect: Generate content/audio")
        self.query_one("#detail-body", Static).update(
            "Inspecting generated content and audio freshness. This does not call Gemini or TTS."
        )
        self._render_sync_stages(show=False)
        action_output = self.query_one("#action-output", Static)
        action_output.display = True
        action_output.update("\n".join(["[bold]Content/audio state[/bold]", self._content_audio_preview_body()]))
        self._render_commands(self.items[self._item_index("3")], preview=True)
        self.query_one("#safety", Static).update("Read-only. No Gemini, TTS, or live Anki action was run.")

    def _card_input_value(self, selector: str) -> str:
        return self.query_one(selector, Input).value.strip()

    def _set_card_input_value(self, selector: str, value: str) -> None:
        self.query_one(selector, Input).value = value

    def _find_note(self, hanzi: str) -> CharacterNote | None:
        try:
            notes = self.runtime.note_store.load()
        except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None
        return next((note for note in notes if note.hanzi == hanzi), None)

    def _load_card_editor(self) -> None:
        from ..notes import load_overrides

        key = self._card_input_value("#card-hanzi")
        action_output = self.query_one("#action-output", Static)
        action_output.display = True
        if not key:
            action_output.update("[yellow]Enter a character to load.[/yellow]")
            return

        note = self._find_note(key)
        override = load_overrides(self.runtime.overrides_path).get(key, {})
        if note is None:
            action_output.update(f"[yellow]{key} is not in saved enriched state.[/yellow]")
            return

        self._set_card_input_value("#card-meaning", str(override.get("meaning", note.meaning)))
        self._set_card_input_value("#card-sentence", str(override.get("sentence", note.sentence)))
        self._set_card_input_value("#card-sentence-pinyin", str(override.get("sentence_pinyin", note.sentence_pinyin)))
        self._set_card_input_value("#card-sentence-english", str(override.get("sentence_english", note.sentence_english)))
        action_output.update(
            "\n".join(
                [
                    f"[bold]Loaded card:[/bold] {key}",
                    "Edit fields and press s to save overrides.",
                ]
            )
        )

    def _save_card_editor(self) -> None:
        from ..cli.app import AppRuntime
        from ..cli.card import run_card_set

        key = self._card_input_value("#card-hanzi")
        action_output = self.query_one("#action-output", Static)
        action_output.display = True
        if not key:
            action_output.update("[yellow]Enter a character before saving.[/yellow]")
            return

        updates = {
            "meaning": self._card_input_value("#card-meaning") or None,
            "sentence": self._card_input_value("#card-sentence") or None,
            "sentence_pinyin": self._card_input_value("#card-sentence-pinyin") or None,
            "sentence_english": self._card_input_value("#card-sentence-english") or None,
        }
        if not any(value is not None for value in updates.values()):
            action_output.update("[yellow]Enter at least one field before saving.[/yellow]")
            return

        output = self._capture_runtime_output(
            lambda: run_card_set(cast(AppRuntime, self.runtime), key, **updates)
        )
        self._refresh_plan()
        self._render_sync_stages(show=False)
        self._render_commands(self.items[self._item_index("2")], preview=True)
        action_output.update("\n".join(["[bold]Saved card override[/bold]", output]))
        self.query_one("#safety", Static).update("Local manual override saved. No live Anki state was changed.")

    def _preview_body(self, item: WorkflowItem) -> str:
        if item.key == "1":
            return "Dry-run rebuild preview. This only explains stale stages and required work."
        if item.key == "2":
            return self._card_preview_body()
        if item.key == "3":
            return self._content_audio_preview_body()
        if item.key == "4":
            return (
                "Song planning needs current live Anki state. The first cockpit slice keeps this "
                "as a preview-only handoff; the next slice should run the existing songs planner "
                "inside the dashboard and require confirmation before activation."
            )
        if item.key == "5":
            return self._health_preview_body()
        return item.detail

    def _card_preview_body(self) -> str:
        try:
            notes = self.runtime.note_store.load()
        except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            return f"Could not load enriched notes: {error}\nRun health checks before editing cards."

        issues = validation_issues(notes)
        flagged = flagged_notes(notes)
        return "\n".join(
            [
                f"Loaded {len(notes)} notes.",
                f"Validation issues: {len(issues)}",
                f"Flagged for review: {len(flagged)}",
                "Next interactive slice: search/select a character and save overrides through the card workflow.",
            ]
        )

    def _content_audio_preview_body(self) -> str:
        try:
            notes = self.runtime.note_store.load()
            profiles = audio_generation_profiles(self.runtime.tts_provider, self.runtime.sentence_tts_provider)
            audio_state = build_audio_deck_state(
                notes,
                profiles=profiles,
                generated_audio_dir=self.runtime.generated_audio_dir,
                manifest=load_audio_manifest(self.runtime.audio_manifest_path),
            )
        except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            return f"Could not inspect content/audio state: {error}"

        pending = audio_state.pending_counts_by_kind()
        return "\n".join(
            [
                f"Loaded {len(notes)} notes.",
                f"Notes needing audio updates: {audio_state.pending_notes}",
                f"Pending audio: Mandarin {pending['mandarin']}, Cantonese {pending['cantonese']}, Sentence {pending['sentence']}",
                f"Orphaned generated audio files: {len(audio_state.orphaned_files)}",
            ]
        )

    def _health_preview_body(self) -> str:
        assert self.plan is not None
        lines = [
            f"Source deck: {'present' if self.runtime.source_deck_path.is_file() else 'missing'}",
            f"Enriched state: {'present' if self.runtime.note_store.exists() else 'missing'}",
            f"Built deck: {'present' if self.runtime.deck_output_path.is_file() else 'missing'}",
            f"Sync plan: {sync_summary(self.plan)}",
            "AnkiConnect: not probed from this preview; use doctor --check-anki when Anki is open.",
        ]
        return "\n".join(lines)

    def _render_commands(self, item: WorkflowItem, *, preview: bool = False) -> None:
        commands = self.query_one("#commands", Static)
        if item.key == "1":
            assert self.plan is not None
            if self.plan.required_commands:
                rendered = "\n".join(
                    [
                        "[bold]Command equivalents[/bold]",
                        "  uv run anki-chinese sync --dry-run",
                        *[f"  uv run {command}" for command in self.plan.required_commands],
                    ]
                )
            else:
                rendered = "\n".join(
                    [
                        "[green]No sync steps required[/green]",
                        "  uv run anki-chinese sync --dry-run",
                    ]
                )
            commands.update(rendered)
            return

        if item.commands:
            title = "Command equivalents" if preview else "Advanced command equivalents"
            rendered = "\n".join([f"[bold]{title}[/bold]", *[f"  {command}" for command in item.commands]])
        else:
            rendered = ""
        commands.update(rendered)


def run_dashboard(runtime: DashboardRuntime) -> None:
    """Run the interactive Textual dashboard."""

    DashboardApp(runtime).run()
