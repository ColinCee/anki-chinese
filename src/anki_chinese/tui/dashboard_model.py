"""Dashboard workflow data and sync-plan helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from rich.console import Console

from ..audio import TTSProvider
from ..notes import JsonNoteStore
from ..workflows.sync import SyncPlan, plan_sync


class DashboardRuntime(Protocol):
    source_deck_path: Path
    overrides_path: Path
    note_store: JsonNoteStore
    generated_audio_dir: Path
    deck_output_path: Path
    pipeline_state_path: Path
    audio_manifest_path: Path
    tts_provider: TTSProvider
    sentence_tts_provider: TTSProvider | None
    console: Console


@dataclass(frozen=True)
class WorkflowItem:
    key: str
    label: str
    detail: str
    commands: tuple[str, ...] = ()
    safety: str = ""


WORKFLOW_ITEMS = (
    WorkflowItem("1", "Sync & rebuild", "Show the current init/audio/build plan"),
    WorkflowItem(
        "2",
        "Review / edit cards",
        "Inspect cards, write manual overrides, then let sync rebuild what changed",
        (
            "uv run anki-chinese status",
            "uv run anki-chinese review",
            "uv run anki-chinese card show <hanzi>",
            "uv run anki-chinese card set <hanzi> --sentence ...",
            "uv run anki-chinese sync --dry-run",
        ),
    ),
    WorkflowItem(
        "3",
        "Generate sentences/audio",
        "Generate or repair content, then refresh stale audio and deck output",
        (
            "uv run anki-chinese sentences --char <hanzi>",
            "uv run anki-chinese keywords",
            "uv run anki-chinese audio",
            "uv run anki-chinese sync --dry-run",
        ),
    ),
    WorkflowItem(
        "4",
        "Song study planner",
        "Use the high-level learn/undo workflow for human song study",
        (
            "uv run anki-chinese songs analyze",
            "uv run anki-chinese songs next --limit 20",
            "uv run anki-chinese songs learn --limit 20",
            "uv run anki-chinese songs learn --limit 20 --confirm",
            "uv run anki-chinese songs undo",
        ),
        "Live Anki changes preview by default; use --confirm only after reviewing counts.",
    ),
    WorkflowItem(
        "5",
        "Activate / unsuspend in Anki",
        "Preview explicit character activation before mutating live Anki",
        (
            "uv run anki-chinese activate chars <chars> --dry-run",
            "uv run anki-chinese activate chars <chars> --confirm",
            "uv run anki-chinese activate snapshots list",
            "uv run anki-chinese activate undo latest",
        ),
        "Confirmed activation writes an undo snapshot before unsuspending cards.",
    ),
    WorkflowItem(
        "6",
        "Health, cleanup, undo",
        "Check deck/audio health and inspect reversible live-state snapshots",
        (
            "uv run anki-chinese doctor",
            "uv run anki-chinese status",
            "uv run anki-chinese audio-clean",
            "uv run anki-chinese activate snapshots list",
            "uv run anki-chinese activate snapshots show <snapshot>",
        ),
        "Snapshot inspection is local-file only; undo previews before live changes.",
    ),
)


def current_sync_plan(runtime: DashboardRuntime) -> SyncPlan:
    return plan_sync(
        source_deck_path=runtime.source_deck_path,
        overrides_path=runtime.overrides_path,
        enriched_path=runtime.note_store.path,
        deck_output_path=runtime.deck_output_path,
        generated_audio_dir=runtime.generated_audio_dir,
        tts_provider=runtime.tts_provider,
        sentence_tts_provider=runtime.sentence_tts_provider,
        audio_manifest_path=runtime.audio_manifest_path,
        pipeline_state_path=runtime.pipeline_state_path,
    )


def sync_summary(plan: SyncPlan) -> str:
    needed = sum(1 for stage in plan.stages if stage.status == "needed")
    blocked = sum(1 for stage in plan.stages if stage.status == "blocked")
    skipped = sum(1 for stage in plan.stages if stage.status == "skipped")
    if plan.is_up_to_date:
        return "up to date"
    parts: list[str] = []
    if needed:
        parts.append(f"{needed} needed")
    if blocked:
        parts.append(f"{blocked} blocked")
    if skipped:
        parts.append(f"{skipped} skipped")
    return ", ".join(parts)


def recommended_command(plan: SyncPlan) -> str:
    return plan.required_commands[0] if plan.required_commands else "No sync steps required"
