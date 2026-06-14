"""Durable pipeline state for rebuild workflow stages."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

PipelineStageId = Literal["init", "audio", "build"]
FingerprintKind = Literal["file", "directory", "missing"]


def _fingerprint_kind(value: object) -> FingerprintKind:
    if value in {"file", "directory", "missing"}:
        return cast(FingerprintKind, value)
    return "missing"


def _stage_id(value: object) -> PipelineStageId | None:
    if value in {"init", "audio", "build"}:
        return cast(PipelineStageId, value)
    return None


def _object_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return {}


def _int_value(value: object, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


@dataclass(frozen=True)
class PathFingerprint:
    path: str
    kind: FingerprintKind
    size: int = 0
    mtime_ns: int = 0
    entries: int = 0
    metadata_hash: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "kind": self.kind,
            "size": self.size,
            "mtime_ns": self.mtime_ns,
            "entries": self.entries,
            "metadata_hash": self.metadata_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PathFingerprint:
        return cls(
            path=str(data["path"]),
            kind=_fingerprint_kind(data.get("kind")),
            size=_int_value(data.get("size")),
            mtime_ns=_int_value(data.get("mtime_ns")),
            entries=_int_value(data.get("entries")),
            metadata_hash=str(data.get("metadata_hash", "")),
        )


@dataclass(frozen=True)
class StageState:
    stage: PipelineStageId
    completed_at: str
    inputs: dict[str, PathFingerprint]
    outputs: dict[str, PathFingerprint]

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "completed_at": self.completed_at,
            "inputs": {name: fingerprint.to_dict() for name, fingerprint in self.inputs.items()},
            "outputs": {name: fingerprint.to_dict() for name, fingerprint in self.outputs.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> StageState:
        stage = _stage_id(data.get("stage")) or "init"
        return cls(
            stage=stage,
            completed_at=str(data["completed_at"]),
            inputs={
                name: PathFingerprint.from_dict(_object_dict(fingerprint))
                for name, fingerprint in _object_dict(data.get("inputs")).items()
            },
            outputs={
                name: PathFingerprint.from_dict(_object_dict(fingerprint))
                for name, fingerprint in _object_dict(data.get("outputs")).items()
            },
        )


@dataclass(frozen=True)
class PipelineState:
    version: int
    stages: dict[PipelineStageId, StageState]

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "stages": {stage: state.to_dict() for stage, state in self.stages.items()},
        }

    @classmethod
    def empty(cls) -> PipelineState:
        return cls(version=1, stages={})

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PipelineState:
        stages: dict[PipelineStageId, StageState] = {}
        for stage_key, state in _object_dict(data.get("stages")).items():
            stage = _stage_id(stage_key)
            if stage is None:
                continue
            stages[stage] = StageState.from_dict(_object_dict(state))
        return cls(version=_int_value(data.get("version"), default=1), stages=stages)


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def fingerprint_path(path: Path) -> PathFingerprint:
    """Return a cheap metadata fingerprint for a file, directory, or missing path."""

    if not path.exists():
        return PathFingerprint(path=_relative_path(path), kind="missing")

    if path.is_file():
        stat = path.stat()
        return PathFingerprint(
            path=_relative_path(path),
            kind="file",
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            metadata_hash=hashlib.sha256(
                f"{path.name}\0{stat.st_size}\0{stat.st_mtime_ns}".encode()
            ).hexdigest(),
        )

    files = [child for child in path.rglob("*") if child.is_file()]
    digest = hashlib.sha256()
    total_size = 0
    latest_mtime_ns = 0
    for child in sorted(files):
        stat = child.stat()
        total_size += stat.st_size
        latest_mtime_ns = max(latest_mtime_ns, stat.st_mtime_ns)
        relative = child.relative_to(path)
        digest.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())

    return PathFingerprint(
        path=_relative_path(path),
        kind="directory",
        size=total_size,
        mtime_ns=latest_mtime_ns,
        entries=len(files),
        metadata_hash=digest.hexdigest(),
    )


def load_pipeline_state(path: Path) -> PipelineState:
    if not path.exists():
        return PipelineState.empty()
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        return PipelineState.empty()
    return PipelineState.from_dict(data)


def save_pipeline_state(path: Path, state: PipelineState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def record_stage(
    path: Path,
    stage: PipelineStageId,
    *,
    inputs: dict[str, Path],
    outputs: dict[str, Path],
) -> PipelineState:
    state = load_pipeline_state(path)
    stages = dict(state.stages)
    stages[stage] = StageState(
        stage=stage,
        completed_at=datetime.now(UTC).isoformat(),
        inputs={name: fingerprint_path(input_path) for name, input_path in inputs.items()},
        outputs={name: fingerprint_path(output_path) for name, output_path in outputs.items()},
    )
    next_state = PipelineState(version=state.version, stages=stages)
    save_pipeline_state(path, next_state)
    return next_state
