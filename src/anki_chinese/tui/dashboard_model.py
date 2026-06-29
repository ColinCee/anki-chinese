"""Dashboard workflow data and sync-plan helpers."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from rich.console import Console

from ..activation import AnkiConnectClient, AnkiConnectError
from ..audio import TTSProvider
from ..audio.state import audio_generation_profiles, build_audio_deck_state, load_audio_manifest
from ..notes import JsonNoteStore, flagged_notes, validation_issues
from ..songs import (
    SongProgressRow,
    analyze_song_corpus,
    find_song,
    load_songs,
    plan_song_activation,
)
from ..workflows.sync import SyncPlan, SyncStagePlan, plan_sync


class DashboardRuntime(Protocol):
    source_deck_path: Path
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


@dataclass(frozen=True)
class TodayView:
    sync_state: str
    recommendation: DashboardRecommendation
    primary_action: str
    safety_level: str


@dataclass(frozen=True)
class RebuildStageView:
    label: str
    status: str
    reason: str
    action: str
    marker: str


@dataclass(frozen=True)
class RebuildView:
    sync_state: str
    generated_deck: str
    can_run: bool
    run_label: str
    stages: tuple[RebuildStageView, ...]


class SongKnowledgeClient(Protocol):
    def find_active_characters(self) -> set[str]: ...

    def find_studied_characters(self) -> set[str]: ...

    def find_all_deck_info(self) -> tuple[list[str], set[str]]: ...


@dataclass(frozen=True)
class SongBrowserRowView:
    title: str
    known_percent: int
    new_deck_count: int
    activation_count: int
    non_deck_count: int
    ready: str
    selected: bool


@dataclass(frozen=True)
class SongBrowserView:
    error: str | None
    song_titles: tuple[str, ...] = ()
    selected_index: int = -1
    song_label: str = ""
    reason: str = ""
    new_chars_count: int = 0
    already_active_count: int = 0
    non_deck_count: int = 0
    chars: tuple[str, ...] = ()
    known: int = 0
    total_chars: int = 0
    known_percent: int = 0
    new_deck_count: int = 0
    activation_count: int = 0
    pace: int = 0
    days: int = 0
    rows: tuple[SongBrowserRowView, ...] = ()
    hidden_row_count: int = 0


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


def today_view(runtime: DashboardRuntime, plan: SyncPlan) -> TodayView:
    recommendation = recommend_workflow(runtime, plan)
    item = WORKFLOW_ITEMS[_workflow_index(recommendation.workflow_key)]
    return TodayView(
        sync_state=sync_summary(plan),
        recommendation=recommendation,
        primary_action=item.primary_action,
        safety_level=_workflow_safety_level(recommendation.workflow_key),
    )


def build_rebuild_view(runtime: DashboardRuntime, plan: SyncPlan) -> RebuildView:
    stages = tuple(_rebuild_stage_view(stage) for stage in plan.stages)
    can_run = any(stage.status in {"needed", "skipped"} for stage in plan.stages) and not any(
        stage.status == "blocked" for stage in plan.stages
    )
    deck_state = "present" if runtime.deck_output_path.is_file() else "not built yet"
    return RebuildView(
        sync_state=sync_summary(plan),
        generated_deck=f"{runtime.deck_output_path} ({deck_state})",
        can_run=can_run,
        run_label="Run local rebuild" if can_run else "No rebuild can run now",
        stages=stages,
    )


def format_rebuild_view(view: RebuildView) -> str:
    lines = [
        "[bold]Rebuild plan[/bold]",
        f"State: {view.sync_state}",
        f"Generated deck: {view.generated_deck}",
        f"Action: {view.run_label}",
        "",
        "[bold]Stages[/bold]",
    ]
    for stage in view.stages:
        lines.extend(
            [
                f"{stage.marker} {stage.label}",
                f"  Status: {stage.status}",
                f"  Why: {stage.reason}",
                f"  Next: {stage.action}",
            ]
        )
    return "\n".join(lines)


def build_song_browser_view(
    runtime: DashboardRuntime,
    *,
    song_query: str,
    limit: int,
    pace: int,
    client_factory: Callable[[str], SongKnowledgeClient] | None = None,
) -> SongBrowserView:
    songs = load_songs(runtime.song_lyrics_dir)
    if not songs:
        return SongBrowserView(error=f"[yellow]No lyric files found in {runtime.song_lyrics_dir}[/yellow]")

    factory = client_factory or _default_song_client
    client = factory(os.getenv("ANKICONNECT_API_KEY", "").strip())
    try:
        active_chars = client.find_active_characters()
        studied_chars = client.find_studied_characters()
        deck_order, deck_chars = client.find_all_deck_info()
    except AnkiConnectError as error:
        return SongBrowserView(
            error="\n".join(
                [
                    "[red]Could not read live Anki state.[/red]",
                    str(error),
                    "Open Anki with AnkiConnect installed, then retry.",
                ]
            )
        )

    analysis = analyze_song_corpus(
        songs,
        active_chars=active_chars,
        learned_chars=studied_chars,
        deck_chars=deck_chars,
        pace=pace,
    )
    selected_row = _selected_song_row(analysis.sequence, song_query=song_query)
    if selected_row is None:
        return SongBrowserView(error=f"[yellow]Song not found or ambiguous:[/yellow] {song_query}")

    activation_plan = plan_song_activation(
        selected_row.song,
        active_chars=active_chars,
        deck_chars=deck_chars,
        deck_order=deck_order,
        limit=limit,
    )
    rows = _song_browser_rows(analysis.sequence, selected_row=selected_row)
    selected_index = next(index for index, row in enumerate(analysis.sequence) if row == selected_row)
    return SongBrowserView(
        error=None,
        song_titles=tuple(row.song.title for row in analysis.sequence),
        selected_index=selected_index,
        song_label=selected_row.song.label,
        reason=_song_reason(selected_row, song_query=song_query),
        new_chars_count=len(activation_plan.chars),
        already_active_count=len(activation_plan.already_active),
        non_deck_count=len(activation_plan.non_deck_chars),
        chars=activation_plan.chars,
        known=selected_row.known,
        total_chars=selected_row.chars,
        known_percent=selected_row.known_percent,
        new_deck_count=len(selected_row.new_deck_chars),
        activation_count=len(selected_row.activation_deck_chars),
        pace=pace,
        days=selected_row.days,
        rows=tuple(rows),
        hidden_row_count=max(len(analysis.sequence) - len(rows), 0),
    )


def format_song_browser_view(view: SongBrowserView) -> str:
    if view.error is not None:
        return view.error

    rows = ["Song | Known | New | Activate | Non-deck | Ready"]
    for row in view.rows:
        marker = ">" if row.selected else " "
        rows.append(
            f"{marker} {row.title} | {row.known_percent}% | "
            f"{row.new_deck_count} | {row.activation_count} | {row.non_deck_count} | {row.ready}"
        )
    if view.hidden_row_count:
        rows.append(f"... {view.hidden_row_count} more songs")

    return "\n".join(
        [
            "[bold]Recommended next song[/bold]",
            view.song_label,
            f"Why: {view.reason}",
            "",
            "[bold]Next batch[/bold]",
            f"New chars: {view.new_chars_count}",
            f"Already active: {view.already_active_count}",
            f"Not in deck: {view.non_deck_count}",
            f"Chars: {' '.join(view.chars) if view.chars else 'none'}",
            "",
            "[bold]Song detail[/bold]",
            f"Known in song: {view.known}/{view.total_chars} ({view.known_percent}%)",
            f"New in deck: {view.new_deck_count}",
            f"Would activate: {view.activation_count} chars before limit",
            f"Estimated days at pace {view.pace}: ~{view.days}",
            "",
            "[bold]All songs[/bold]",
            *rows,
            "",
            "[dim]Enter a song title, press x to inspect, or use n/b to move. Activation remains confirm-gated.[/dim]",
        ]
    )


def _default_song_client(api_key: str) -> SongKnowledgeClient:
    return AnkiConnectClient(api_key=api_key)


def _selected_song_row(
    rows: list[SongProgressRow],
    *,
    song_query: str,
) -> SongProgressRow | None:
    if song_query:
        songs = [row.song for row in rows]
        song = find_song(songs, song_query)
        if song is None:
            return None
        return next(row for row in rows if row.song == song)
    return next((row for row in rows if row.activation_deck_chars), rows[0] if rows else None)


def _song_reason(row: SongProgressRow, *, song_query: str) -> str:
    if song_query:
        return "selected song"
    if row.activation_deck_chars:
        return "first song with inactive in-deck characters"
    return "all songs are already active or outside the deck"


def _song_browser_rows(
    rows: list[SongProgressRow],
    *,
    selected_row: SongProgressRow,
) -> list[SongBrowserRowView]:
    rendered: list[SongBrowserRowView] = []
    for row in rows[:12]:
        ready = "next" if row == selected_row else ("learned" if not row.activation_deck_chars else "later")
        rendered.append(
            SongBrowserRowView(
                title=row.song.title,
                known_percent=row.known_percent,
                new_deck_count=len(row.new_deck_chars),
                activation_count=len(row.activation_deck_chars),
                non_deck_count=len(row.non_deck_chars),
                ready=ready,
                selected=row == selected_row,
            )
        )
    return rendered


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


def _workflow_index(key: str) -> int:
    return next((index for index, item in enumerate(WORKFLOW_ITEMS) if item.key == key), 0)


def _workflow_safety_level(workflow_key: str) -> str:
    if workflow_key == "1":
        return "Safe local rebuild; no live Anki mutation."
    if workflow_key == "2":
        return "Local source-deck edit; downstream rebuild preview follows."
    if workflow_key == "3":
        return "Read-only inspection until generation is explicitly run."
    if workflow_key == "4":
        return "Read-only song analysis; activation stays confirm-gated."
    if workflow_key == "5":
        return "Read-only checks by default; restore actions need confirmation."
    return "Preview first; confirm before mutation."


def _rebuild_stage_view(stage: SyncStagePlan) -> RebuildStageView:
    if stage.status == "up_to_date":
        marker = "[green]✓[/green]"
        action = "current"
    elif stage.status == "needed":
        marker = "[yellow]→[/yellow]"
        action = "will run when local rebuild starts"
    elif stage.status == "blocked":
        marker = "[red]![/red]"
        action = "blocked; fix precondition first"
    else:
        marker = "[dim]-[/dim]"
        action = "skipped unless dependency changes"
    return RebuildStageView(
        label=stage.label,
        status=stage.status,
        reason=stage.reason,
        action=action,
        marker=marker,
    )
