"""Workbench workflow data and sync-plan helpers."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from rich.console import Console

from ..activation import AnkiConnectClient, AnkiConnectError, list_activation_snapshots
from ..audio import TTSProvider
from ..audio.state import audio_generation_profiles, build_audio_deck_state, load_audio_manifest
from ..config import ANKI_BACKUP_DIR
from ..notes import CharacterNote, JsonNoteStore, flagged_notes, validation_issues
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

    @property
    def source_content_path(self) -> Path:
        ...


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


@dataclass(frozen=True)
class CardCandidateView:
    hanzi: str
    meaning: str
    reason: str


@dataclass(frozen=True)
class CardSearchView:
    error: str | None
    selected: CardCandidateView | None = None
    candidates: tuple[CardCandidateView, ...] = ()


@dataclass(frozen=True)
class CardFieldChange:
    field: str
    before: str
    after: str


@dataclass(frozen=True)
class CardEditView:
    hanzi: str
    changes: tuple[CardFieldChange, ...]
    sync_impact: str


@dataclass(frozen=True)
class CredentialView:
    label: str
    ready: bool
    detail: str


@dataclass(frozen=True)
class ContentAudioView:
    error: str | None
    note_count: int = 0
    missing_sentence_count: int = 0
    missing_translation_count: int = 0
    notes_needing_audio: int = 0
    pending_mandarin: int = 0
    pending_cantonese: int = 0
    pending_sentence: int = 0
    orphaned_audio_count: int = 0
    credentials: tuple[CredentialView, ...] = ()


@dataclass(frozen=True)
class SnapshotView:
    filename: str
    operation: str
    character_count: int
    note_count: int
    mutation_card_count: int
    chars_preview: str


@dataclass(frozen=True)
class HealthUndoView:
    source_state: str
    enriched_state: str
    built_deck_state: str
    sync_state: str
    snapshots: tuple[SnapshotView, ...]
    undo_preview: str


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
        source_deck_path=runtime.source_content_path,
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


def build_card_search_view(runtime: DashboardRuntime, query: str, *, limit: int = 8) -> CardSearchView:
    try:
        notes = runtime.note_store.load()
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        return CardSearchView(error=f"Could not load cards: {error}")

    term = query.strip()
    if not term:
        flagged = flagged_notes(notes)
        candidates = tuple(_card_candidate(note, reason="flagged for review") for note in flagged[:limit])
        return CardSearchView(error=None, selected=candidates[0] if candidates else None, candidates=candidates)

    exact = next((note for note in notes if note.hanzi == term), None)
    if exact is not None:
        candidate = _card_candidate(exact, reason="exact character match")
        return CardSearchView(error=None, selected=candidate, candidates=(candidate,))

    matches: list[CardCandidateView] = []
    for note in notes:
        haystacks = {
            "meaning": note.meaning,
            "pinyin": note.pinyin,
            "sentence": note.sentence,
            "english": note.sentence_english,
        }
        reason = next((name for name, value in haystacks.items() if term.lower() in value.lower()), "")
        if reason:
            matches.append(_card_candidate(note, reason=f"matched {reason}"))
        if len(matches) >= limit:
            break
    return CardSearchView(error=None, selected=matches[0] if matches else None, candidates=tuple(matches))


def format_card_search_view(view: CardSearchView) -> str:
    if view.error is not None:
        return view.error
    if not view.candidates:
        return "[yellow]No matching cards found.[/yellow]"

    lines = ["[bold]Card search[/bold]"]
    for candidate in view.candidates:
        marker = ">" if candidate == view.selected else " "
        lines.append(f"{marker} {candidate.hanzi} · {candidate.meaning} · {candidate.reason}")
    lines.append("")
    lines.append("[dim]Selected card loaded into the form. Edit fields, then press s to save.[/dim]")
    return "\n".join(lines)


def build_card_edit_view(note: CharacterNote, updates: dict[str, str | None], sync_impact: str) -> CardEditView:
    changes: list[CardFieldChange] = []
    for field_name, after in updates.items():
        if after is None:
            continue
        before = str(getattr(note, field_name))
        if before != after:
            changes.append(CardFieldChange(field=field_name, before=before, after=after))
    if "sentence" in {change.field for change in changes} and note.sentence_audio:
        changes.append(CardFieldChange(field="sentence_audio", before=note.sentence_audio, after=""))
    return CardEditView(hanzi=note.hanzi, changes=tuple(changes), sync_impact=sync_impact)


def format_card_edit_view(view: CardEditView) -> str:
    if not view.changes:
        return f"[yellow]No field changes for {view.hanzi}.[/yellow]"
    lines = [
        f"[bold]Saved source deck edit[/bold] {view.hanzi}",
        "[bold]Changed fields[/bold]",
    ]
    for change in view.changes:
        lines.extend(
            [
                f"{change.field}:",
                f"  before: {change.before or 'empty'}",
                f"  after: {change.after or 'empty'}",
            ]
        )
    lines.extend(["", f"Downstream sync: {view.sync_impact}"])
    return "\n".join(lines)


def build_content_audio_view(runtime: DashboardRuntime) -> ContentAudioView:
    try:
        notes = runtime.note_store.load()
        profiles = audio_generation_profiles(runtime.tts_provider, runtime.sentence_tts_provider)
        audio_state = build_audio_deck_state(
            notes,
            profiles=profiles,
            generated_audio_dir=runtime.generated_audio_dir,
            manifest=load_audio_manifest(runtime.audio_manifest_path),
        )
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        return ContentAudioView(error=f"Could not inspect content/audio state: {error}")

    pending = audio_state.pending_counts_by_kind()
    return ContentAudioView(
        error=None,
        note_count=len(notes),
        missing_sentence_count=sum(1 for note in notes if not note.sentence.strip()),
        missing_translation_count=sum(1 for note in notes if not note.sentence_english.strip()),
        notes_needing_audio=audio_state.pending_notes,
        pending_mandarin=pending["mandarin"],
        pending_cantonese=pending["cantonese"],
        pending_sentence=pending["sentence"],
        orphaned_audio_count=len(audio_state.orphaned_files),
        credentials=_credential_views(),
    )


def format_content_audio_view(view: ContentAudioView) -> str:
    if view.error is not None:
        return view.error

    lines = [
        "[bold]Content/audio tasks[/bold]",
        f"Loaded notes: {view.note_count}",
        f"Missing example sentences: {view.missing_sentence_count}",
        f"Missing sentence translations: {view.missing_translation_count}",
        f"Notes needing audio updates: {view.notes_needing_audio}",
        (
            "Pending audio: "
            f"Mandarin {view.pending_mandarin}, Cantonese {view.pending_cantonese}, Sentence {view.pending_sentence}"
        ),
        f"Orphaned generated audio files: {view.orphaned_audio_count}",
        "",
        "[bold]Credential readiness[/bold]",
    ]
    for credential in view.credentials:
        marker = "[green]ready[/green]" if credential.ready else "[yellow]setup needed[/yellow]"
        lines.append(f"{credential.label}: {marker} · {credential.detail}")
    lines.extend(
        [
            "",
            "[bold]Next safe action[/bold]",
            "Review this plan first. Generation uses external providers, so command equivalents stay behind Advanced.",
        ]
    )
    return "\n".join(lines)


def build_health_undo_view(
    runtime: DashboardRuntime,
    plan: SyncPlan,
    *,
    snapshot_dir: Path = ANKI_BACKUP_DIR,
    snapshot_limit: int = 5,
) -> HealthUndoView:
    snapshots = tuple(_snapshot_view(snapshot) for snapshot in list_activation_snapshots(snapshot_dir, limit=snapshot_limit))
    latest = snapshots[0] if snapshots else None
    undo_preview = (
        f"Latest restore preview would use {latest.filename}: {latest.mutation_card_count} cards across {latest.note_count} notes."
        if latest is not None
        else "No activation snapshots available to restore."
    )
    return HealthUndoView(
        source_state="present" if runtime.source_content_path.is_file() else "missing",
        enriched_state="present" if runtime.note_store.exists() else "missing",
        built_deck_state="present" if runtime.deck_output_path.is_file() else "missing",
        sync_state=sync_summary(plan),
        snapshots=snapshots,
        undo_preview=undo_preview,
    )


def format_health_undo_view(view: HealthUndoView) -> str:
    lines = [
        "[bold]Health and undo[/bold]",
        f"Source deck: {view.source_state}",
        f"Enriched state: {view.enriched_state}",
        f"Built deck: {view.built_deck_state}",
        f"Sync plan: {view.sync_state}",
        "AnkiConnect: not probed from this preview.",
        "",
        "[bold]Recent activation snapshots[/bold]",
    ]
    if view.snapshots:
        for snapshot in view.snapshots:
            chars = f" · {snapshot.chars_preview}" if snapshot.chars_preview else ""
            lines.append(
                f"{snapshot.filename}: {snapshot.operation}, {snapshot.mutation_card_count} cards, "
                f"{snapshot.note_count} notes{chars}"
            )
    else:
        lines.append("No activation snapshots found.")
    lines.extend(
        [
            "",
            "[bold]Undo preview[/bold]",
            view.undo_preview,
            "Restore remains confirm-gated and writes a safety snapshot before live mutation.",
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

    if not runtime.source_content_path.is_file() or not runtime.note_store.exists():
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


def _card_candidate(note: CharacterNote, *, reason: str) -> CardCandidateView:
    return CardCandidateView(hanzi=note.hanzi, meaning=note.meaning or "no meaning", reason=reason)


def _credential_views() -> tuple[CredentialView, ...]:
    google_adc = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    return (
        CredentialView(
            "Gemini",
            bool(os.getenv("GEMINI_API_KEY", "").strip()),
            "GEMINI_API_KEY controls sentence/keyword generation",
        ),
        CredentialView(
            "Google TTS",
            bool(google_adc),
            "GOOGLE_APPLICATION_CREDENTIALS set" if google_adc else "set GOOGLE_APPLICATION_CREDENTIALS or use gcloud ADC",
        ),
        CredentialView(
            "MiniMax TTS",
            bool(os.getenv("MINIMAX_API_KEY", "").strip()),
            "MINIMAX_API_KEY controls MiniMax sentence TTS",
        ),
    )


def _snapshot_view(snapshot) -> SnapshotView:
    chars = snapshot.found_chars
    preview = " ".join(chars[:8])
    if len(chars) > 8:
        preview += f" +{len(chars) - 8}"
    return SnapshotView(
        filename=snapshot.path.name,
        operation=snapshot.operation,
        character_count=len(chars),
        note_count=snapshot.note_count,
        mutation_card_count=snapshot.mutation_card_count,
        chars_preview=preview,
    )


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
