"""Textual dashboard for human workflows."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from ..workflows.sync import SyncPlan
from .dashboard_model import (
    WORKFLOW_ITEMS,
    DashboardRuntime,
    WorkflowItem,
    current_sync_plan,
    recommended_command,
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
        height: 5;
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
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, runtime: DashboardRuntime) -> None:
        super().__init__()
        self.runtime = runtime
        self.plan: SyncPlan | None = None
        self.items = WORKFLOW_ITEMS
        self.current_index = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="summary")
        with Vertical(id="body"):
            with Vertical(id="menu-view"):
                yield Label("Workflows", id="workflow-heading")
                yield Static("Choose a workflow, then press Enter.", id="menu-help")
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
                    yield Static("", id="commands")
                    yield Static("", id="safety")
                yield Static("Esc: back · r: refresh · q: quit", id="back-hint")
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

    def action_go_back(self) -> None:
        self._show_menu()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.current_index = event.index
        self._show_workflow(self.items[event.index])

    def _refresh_plan(self) -> None:
        self.plan = current_sync_plan(self.runtime)
        summary = self.query_one("#summary", Static)
        summary.update(
            "\n".join(
                [
                    "[bold]anki-chinese[/bold]",
                    f"Sync: [cyan]{sync_summary(self.plan)}[/cyan]",
                    f"Recommended: [bold]{recommended_command(self.plan)}[/bold]",
                ]
            )
        )

    def _show_workflow(self, item: WorkflowItem) -> None:
        self.query_one("#menu-view", Vertical).display = False
        self.query_one("#detail-view", Vertical).display = True
        self.query_one("#detail-title", Static).update(item.label)
        self.query_one("#detail-body", Static).update(item.detail)
        self._render_sync_stages(show=item.key == "1")
        self._render_commands(item)
        safety = f"Safety: {item.safety}" if item.safety else ""
        self.query_one("#safety", Static).update(safety)

    def _show_menu(self) -> None:
        self.query_one("#menu-view", Vertical).display = True
        self.query_one("#detail-view", Vertical).display = False
        self.query_one("#workflow-list", ListView).focus()

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

    def _render_commands(self, item: WorkflowItem) -> None:
        commands = self.query_one("#commands", Static)
        if item.key == "1":
            assert self.plan is not None
            if self.plan.required_commands:
                rendered = "\n".join(
                    ["[bold]Next commands[/bold]", *[f"  {command}" for command in self.plan.required_commands]]
                )
            else:
                rendered = "[green]No sync steps required[/green]"
            commands.update(rendered)
            return

        if item.commands:
            rendered = "\n".join(["[bold]Useful commands[/bold]", *[f"  {command}" for command in item.commands]])
        else:
            rendered = ""
        commands.update(rendered)


def run_dashboard(runtime: DashboardRuntime) -> None:
    """Run the interactive Textual dashboard."""

    DashboardApp(runtime).run()
