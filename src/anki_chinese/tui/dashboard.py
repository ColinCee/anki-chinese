"""Textual dashboard for human workflows."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, ListItem, ListView, Static

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

    #body {
        height: 1fr;
    }

    #sidebar {
        width: 36;
        border: round $primary;
        margin: 1 0 1 1;
    }

    #content {
        width: 1fr;
        border: round $primary;
        margin: 1;
        padding: 1 2;
    }

    #workflow-list {
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

    DataTable {
        height: auto;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, runtime: DashboardRuntime) -> None:
        super().__init__()
        self.runtime = runtime
        self.plan: SyncPlan | None = None
        self.items = WORKFLOW_ITEMS

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="summary")
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Label("Workflows", id="workflow-heading")
                yield ListView(
                    *[
                        ListItem(
                            Label(f"{item.key}. {item.label}\n[dim]{item.detail}[/dim]"),
                            id=f"workflow-{item.key}",
                        )
                        for item in self.items
                    ],
                    id="workflow-list",
                )
            with Vertical(id="content"):
                yield Static("", id="detail-title")
                yield Static("", id="detail-body")
                yield DataTable(id="sync-table", zebra_stripes=True)
                yield Static("", id="commands")
                yield Static("", id="safety")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "anki-chinese"
        self.sub_title = "workflow dashboard"
        self._refresh_plan()
        self._show_workflow(self.items[0])

    def action_refresh(self) -> None:
        self._refresh_plan()
        list_view = self.query_one("#workflow-list", ListView)
        index = list_view.index or 0
        self._show_workflow(self.items[index])

    def on_list_view_selected(self, event: ListView.Selected) -> None:
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
        self.query_one("#detail-title", Static).update(item.label)
        self.query_one("#detail-body", Static).update(item.detail)
        self._render_sync_table(show=item.key == "1")
        self._render_commands(item)
        safety = f"Safety: {item.safety}" if item.safety else ""
        self.query_one("#safety", Static).update(safety)

    def _render_sync_table(self, *, show: bool) -> None:
        table = self.query_one("#sync-table", DataTable)
        table.clear(columns=True)
        if not show:
            table.display = False
            return

        table.display = True
        table.add_columns("Stage", "Status", "Reason")
        if self.plan is None:
            self._refresh_plan()
        assert self.plan is not None
        for stage in self.plan.stages:
            table.add_row(stage.label, stage.status, stage.reason)

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
