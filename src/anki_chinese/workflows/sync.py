"""State-aware sync planning for deck rebuild workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from ..audio import audio_tasks_for_note
from ..audio.provider import TTSProvider
from ..audio.state import (
    audio_generation_profiles,
    backfill_audio_manifest,
    build_audio_deck_state,
    load_audio_manifest,
)
from ..notes import CharacterNote, load_notes
from .pipeline_state import PipelineState, fingerprint_path, load_pipeline_state

SyncStageId = Literal["init", "audio", "build"]
SyncStageStatus = Literal["needed", "up_to_date", "blocked", "skipped"]


@dataclass(frozen=True)
class SyncStagePlan:
    """One planned sync stage and why it has that status."""

    id: SyncStageId
    label: str
    status: SyncStageStatus
    reason: str
    command: str
    details: dict[str, int | str] | None = None
    last_completed_at: str | None = None
    fingerprints_current: bool | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "id": self.id,
            "label": self.label,
            "status": self.status,
            "reason": self.reason,
            "command": self.command,
        }
        if self.details:
            data["details"] = self.details
        if self.last_completed_at is not None:
            data["last_completed_at"] = self.last_completed_at
        if self.fingerprints_current is not None:
            data["fingerprints_current"] = self.fingerprints_current
        return data


@dataclass(frozen=True)
class SyncPlan:
    """Dry-run sync plan for the rebuild pipeline."""

    stages: list[SyncStagePlan]
    dry_run: bool = True

    @property
    def required_commands(self) -> list[str]:
        return [stage.command for stage in self.stages if stage.status == "needed"]

    @property
    def is_up_to_date(self) -> bool:
        return not any(stage.status in {"needed", "blocked"} for stage in self.stages)

    def to_dict(self) -> dict[str, object]:
        return {
            "dry_run": self.dry_run,
            "up_to_date": self.is_up_to_date,
            "required_commands": self.required_commands,
            "stages": [stage.to_dict() for stage in self.stages],
        }


def _mtime(path: Path) -> float | None:
    if not path.exists():
        return None
    return path.stat().st_mtime


def _is_newer_than_any(path: Path, candidates: list[Path]) -> bool:
    path_mtime = _mtime(path)
    if path_mtime is None:
        return False
    return any((candidate_mtime := _mtime(candidate)) is not None and candidate_mtime > path_mtime for candidate in candidates)


def _generated_audio_newer_than(deck_output_path: Path, generated_audio_dir: Path) -> bool:
    deck_mtime = _mtime(deck_output_path)
    if deck_mtime is None or not generated_audio_dir.is_dir():
        return False
    return any(path.suffix == ".mp3" and path.stat().st_mtime > deck_mtime for path in generated_audio_dir.iterdir())


def _audio_details(
    notes: list[CharacterNote],
    *,
    is_valid_audio_tag: Callable[[str], bool],
) -> dict[str, int | str]:
    pending_notes = 0
    task_counts = {"mandarin": 0, "cantonese": 0, "sentence": 0}
    for note in notes:
        tasks = audio_tasks_for_note(note, force=False, is_valid_audio_tag_fn=is_valid_audio_tag)
        if not tasks:
            continue
        pending_notes += 1
        for task in tasks:
            task_counts[task] += 1

    return {
        "pending_notes": pending_notes,
        "mandarin": task_counts["mandarin"],
        "cantonese": task_counts["cantonese"],
        "sentence": task_counts["sentence"],
    }


def _audio_details_from_state(
    notes: list[CharacterNote],
    *,
    tts_provider: TTSProvider,
    sentence_tts_provider: TTSProvider | None,
    generated_audio_dir: Path,
    audio_manifest_path: Path,
) -> dict[str, int | str]:
    profiles = audio_generation_profiles(tts_provider, sentence_tts_provider)
    manifest = load_audio_manifest(audio_manifest_path)
    audio_state = build_audio_deck_state(
        notes,
        profiles=profiles,
        generated_audio_dir=generated_audio_dir,
        manifest=manifest,
    )
    counts = audio_state.pending_counts_by_kind()
    desired_manifest = backfill_audio_manifest(
        notes,
        profiles=profiles,
        generated_audio_dir=generated_audio_dir,
    )
    manifest_current = not desired_manifest.generated or (
        audio_manifest_path.exists() and manifest == desired_manifest
    )
    return {
        "pending_notes": audio_state.pending_notes,
        "mandarin": counts["mandarin"],
        "cantonese": counts["cantonese"],
        "sentence": counts["sentence"],
        "manifest_entries": len(desired_manifest.generated),
        "manifest_current": 1 if manifest_current else 0,
    }


def _load_notes_if_available(enriched_path: Path) -> list[CharacterNote]:
    if not enriched_path.exists():
        return []
    return load_notes(enriched_path)


def _fingerprints_match(recorded, current_paths: dict[str, Path]) -> bool:
    return all(recorded.get(name) == fingerprint_path(path) for name, path in current_paths.items())


def _with_pipeline_state(
    stage: SyncStagePlan,
    state: PipelineState,
    *,
    inputs: dict[str, Path],
    outputs: dict[str, Path],
) -> SyncStagePlan:
    stage_state = state.stages.get(stage.id)
    if stage_state is None:
        return stage
    return replace(
        stage,
        last_completed_at=stage_state.completed_at,
        fingerprints_current=_fingerprints_match(stage_state.inputs, inputs)
        and _fingerprints_match(stage_state.outputs, outputs),
    )


def plan_sync(
    *,
    source_deck_path: Path,
    overrides_path: Path,
    enriched_path: Path,
    deck_output_path: Path,
    generated_audio_dir: Path,
    is_valid_audio_tag: Callable[[str], bool] | None = None,
    tts_provider: TTSProvider | None = None,
    sentence_tts_provider: TTSProvider | None = None,
    audio_manifest_path: Path | None = None,
    skip_audio: bool = False,
    pipeline_state_path: Path | None = None,
) -> SyncPlan:
    """Return a dry-run plan for bringing generated deck artifacts up to date."""

    stages: list[SyncStagePlan] = []
    pipeline_state = (
        load_pipeline_state(pipeline_state_path) if pipeline_state_path is not None else PipelineState.empty()
    )

    if not source_deck_path.exists():
        init_needed = False
        init_blocked = True
        init_reason = f"Source deck is missing: {source_deck_path}"
    elif not enriched_path.exists():
        init_needed = True
        init_blocked = False
        init_reason = "Enriched state is missing."
    elif _is_newer_than_any(enriched_path, [source_deck_path, overrides_path]):
        init_needed = True
        init_blocked = False
        init_reason = "Source deck or manual overrides changed after enriched state."
    else:
        init_needed = False
        init_blocked = False
        init_reason = "Enriched state is newer than source deck and overrides."

    if init_blocked:
        stages.append(
            _with_pipeline_state(
                SyncStagePlan(
                    id="init",
                    label="Parse + enrich",
                    status="blocked",
                    reason=init_reason,
                    command="anki-chinese init",
                ),
                pipeline_state,
                inputs={
                    "source_deck": source_deck_path,
                    "overrides": overrides_path,
                },
                outputs={"enriched": enriched_path},
            )
        )
    else:
        stages.append(
            _with_pipeline_state(
                SyncStagePlan(
                    id="init",
                    label="Parse + enrich",
                    status="needed" if init_needed else "up_to_date",
                    reason=init_reason,
                    command="anki-chinese init",
                ),
                pipeline_state,
                inputs={
                    "source_deck": source_deck_path,
                    "overrides": overrides_path,
                },
                outputs={"enriched": enriched_path},
            )
        )

    notes = _load_notes_if_available(enriched_path)

    if skip_audio:
        audio_needed = False
        audio_status: SyncStageStatus = "skipped"
        audio_reason = "Audio sync was skipped by option."
        audio_details: dict[str, int | str] | None = None
    elif init_needed or init_blocked:
        audio_needed = False
        audio_status = "blocked"
        audio_reason = "Audio planning waits for parse + enrich to complete."
        audio_details = None
    else:
        if tts_provider is not None and audio_manifest_path is not None:
            audio_details = _audio_details_from_state(
                notes,
                tts_provider=tts_provider,
                sentence_tts_provider=sentence_tts_provider,
                generated_audio_dir=generated_audio_dir,
                audio_manifest_path=audio_manifest_path,
            )
        elif is_valid_audio_tag is not None:
            audio_details = _audio_details(notes, is_valid_audio_tag=is_valid_audio_tag)
        else:
            raise ValueError("plan_sync requires either tts_provider/audio_manifest_path or is_valid_audio_tag")
        audio_needed = int(audio_details["pending_notes"]) > 0 or int(audio_details.get("manifest_current", 1)) == 0
        audio_status = "needed" if audio_needed else "up_to_date"
        if int(audio_details["pending_notes"]) > 0:
            audio_reason = f"{audio_details['pending_notes']} notes need audio updates."
        elif int(audio_details.get("manifest_current", 1)) == 0:
            audio_reason = "Audio provenance manifest is missing or stale."
        else:
            audio_reason = "All expected audio tags are present, valid, and provenance-current."

    stages.append(
        _with_pipeline_state(
            SyncStagePlan(
                id="audio",
                label="Generate audio",
                status=audio_status,
                reason=audio_reason,
                command="anki-chinese audio",
                details=audio_details,
            ),
            pipeline_state,
            inputs={"enriched": enriched_path},
            outputs={"generated_audio": generated_audio_dir},
        )
    )

    if init_blocked:
        build_status: SyncStageStatus = "blocked"
        build_reason = "Build waits for source deck parsing."
    elif init_needed:
        build_status = "blocked"
        build_reason = "Build waits for parse + enrich to update deck state."
    elif audio_needed:
        build_status = "blocked"
        build_reason = "Build waits for audio updates so media is packaged."
    elif not deck_output_path.exists():
        build_status = "needed"
        build_reason = "Deck package is missing."
    elif _is_newer_than_any(deck_output_path, [enriched_path]) or _generated_audio_newer_than(
        deck_output_path, generated_audio_dir
    ):
        build_status = "needed"
        build_reason = "Enriched state or generated audio changed after the deck package."
    else:
        build_status = "up_to_date"
        build_reason = "Deck package is newer than enriched state and generated audio."

    stages.append(
        _with_pipeline_state(
            SyncStagePlan(
                id="build",
                label="Build deck",
                status=build_status,
                reason=build_reason,
                command="anki-chinese build",
            ),
            pipeline_state,
            inputs={
                "enriched": enriched_path,
                "generated_audio": generated_audio_dir,
            },
            outputs={"deck": deck_output_path},
        )
    )

    return SyncPlan(stages=stages)
