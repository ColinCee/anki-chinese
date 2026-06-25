"""Dashboard workflow data and sync-plan helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from rich.console import Console

from ..audio import TTSProvider
from ..audio.state import audio_generation_profiles, build_audio_deck_state, load_audio_manifest
from ..notes import JsonNoteStore, flagged_notes, validation_issues
from ..workflows.sync import SyncPlan, plan_sync


class DashboardRuntime(Protocol):
    source_deck_path: Path
    overrides_path: Path
    song_lyrics_dir: Path
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
    primary_action: str
    commands: tuple[str, ...] = ()
    safety: str = ""


@dataclass(frozen=True)
class DashboardRecommendation:
    workflow_key: str
    title: str
    reason: str


WORKFLOW_ITEMS = (
    WorkflowItem(
        "1",
        "Rebuild deck",
        "Preview the current init/audio/build plan, then run sync when ready.",
        "Preview sync plan",
    ),
    WorkflowItem(
        "2",
        "Improve cards",
        "Find cards that need review, edit one character, then preview the downstream rebuild.",
        "Inspect review state",
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
        "Generate content/audio",
        "Inspect missing generated content and audio before running Gemini or TTS workflows.",
        "Inspect content/audio state",
        (
            "uv run anki-chinese sentences --char <hanzi>",
            "uv run anki-chinese keywords",
            "uv run anki-chinese audio",
            "uv run anki-chinese sync --dry-run",
        ),
    ),
    WorkflowItem(
        "4",
        "Learn songs",
        "Choose a song, preview the next character batch, then confirm snapshot-backed activation.",
        "Preview next song batch",
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
        "Health, cleanup, undo",
        "Run readiness checks, inspect generated-audio cleanup, and recover snapshot-backed live changes.",
        "Inspect health",
        (
            "uv run anki-chinese doctor",
            "uv run anki-chinese status",
            "uv run anki-chinese audio-clean",
            "uv run anki-chinese activate chars <chars> --dry-run",
            "uv run anki-chinese activate snapshots list",
            "uv run anki-chinese activate snapshots show <snapshot>",
            "uv run anki-chinese activate undo latest",
        ),
        "Live changes must preview first and confirmed mutations write undo snapshots.",
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


def recommend_workflow(runtime: DashboardRuntime, plan: SyncPlan) -> DashboardRecommendation:
    """Choose one helpful next workflow without taking over workflow execution."""

    if not runtime.source_deck_path.is_file() or not runtime.note_store.exists():
        return DashboardRecommendation(
            "5",
            "Health, cleanup, undo",
            "Required local deck/state files are missing; run doctor before other workflows.",
        )

    if not plan.is_up_to_date:
        return DashboardRecommendation(
            "1",
            "Rebuild deck",
            f"Generated deck state is not current ({sync_summary(plan)}).",
        )

    try:
        notes = runtime.note_store.load()
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        return DashboardRecommendation(
            "5",
            "Health, cleanup, undo",
            f"Could not read enriched notes: {error}",
        )

    issues = validation_issues(notes)
    flagged = flagged_notes(notes)
    if issues or flagged:
        reason_parts: list[str] = []
        if issues:
            reason_parts.append(f"{len(issues)} validation issues")
        if flagged:
            reason_parts.append(f"{len(flagged)} notes flagged for review")
        return DashboardRecommendation(
            "2",
            "Improve cards",
            "; ".join(reason_parts) + ".",
        )

    profiles = audio_generation_profiles(runtime.tts_provider, runtime.sentence_tts_provider)
    audio_state = build_audio_deck_state(
        notes,
        profiles=profiles,
        generated_audio_dir=runtime.generated_audio_dir,
        manifest=load_audio_manifest(runtime.audio_manifest_path),
    )
    if audio_state.orphaned_files:
        return DashboardRecommendation(
            "5",
            "Health, cleanup, undo",
            f"{len(audio_state.orphaned_files)} orphaned generated audio files can be previewed for cleanup.",
        )

    return DashboardRecommendation(
        "4",
        "Learn songs",
        "Deck rebuild state looks current; choose the next study batch when ready.",
    )
