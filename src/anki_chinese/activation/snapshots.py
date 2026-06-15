"""Read-only activation undo snapshot inspection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SnapshotError(ValueError):
    """Raised when an activation snapshot cannot be read or identified."""


@dataclass(frozen=True)
class ActivationSnapshot:
    path: Path
    data: dict[str, Any]

    @property
    def created_at(self) -> str:
        return str(self.data.get("created_at", ""))

    @property
    def operation(self) -> str:
        return str(self.data.get("operation", "unknown"))

    @property
    def tag(self) -> str:
        return str(self.data.get("tag", ""))

    @property
    def found_chars(self) -> list[str]:
        value = self.data.get("found_chars")
        if isinstance(value, list):
            return [str(item) for item in value]
        value = self.data.get("requested_chars")
        if isinstance(value, list):
            return [str(item) for item in value]
        value = self.data.get("characters")
        if isinstance(value, list):
            chars: list[str] = []
            for item in value:
                if isinstance(item, dict) and "character" in item:
                    chars.append(str(item["character"]))
            return chars
        return []

    def _list_field(self, name: str) -> list[Any]:
        value = self.data.get(name)
        return value if isinstance(value, list) else []

    def _int_list_field(self, name: str) -> tuple[int, ...]:
        values: list[int] = []
        for value in self._list_field(name):
            try:
                values.append(int(value))
            except (TypeError, ValueError):
                continue
        return tuple(values)

    @property
    def note_count(self) -> int:
        return len(self._list_field("note_ids"))

    @property
    def note_ids(self) -> tuple[int, ...]:
        return self._int_list_field("note_ids")

    @property
    def card_count(self) -> int:
        return len(self._list_field("card_ids"))

    @property
    def card_ids(self) -> tuple[int, ...]:
        return self._int_list_field("card_ids")

    @property
    def pre_change_suspended_count(self) -> int:
        return len(self._list_field("pre_change_suspended_card_ids"))

    @property
    def pre_change_suspended_card_ids(self) -> tuple[int, ...]:
        return self._int_list_field("pre_change_suspended_card_ids")

    @property
    def card_ids_to_suspend(self) -> tuple[int, ...]:
        return self._int_list_field("card_ids_to_suspend")

    @property
    def remove_tag(self) -> bool:
        return bool(self.data.get("remove_tag", False))

    @property
    def mutation_card_count(self) -> int:
        if self.operation == "resuspend-tagged-cards":
            return len(self._list_field("card_ids_to_suspend"))
        return self.pre_change_suspended_count

    def summary_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "filename": self.path.name,
            "created_at": self.created_at,
            "operation": self.operation,
            "tag": self.tag,
            "characters": self.found_chars,
            "character_count": len(self.found_chars),
            "note_count": self.note_count,
            "card_count": self.card_count,
            "pre_change_suspended_count": self.pre_change_suspended_count,
            "mutation_card_count": self.mutation_card_count,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary_dict(),
            "snapshot": self.data,
        }


def load_activation_snapshot(path: Path) -> ActivationSnapshot:
    if not path.is_file():
        raise SnapshotError(f"Snapshot not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"Invalid snapshot JSON: {path}") from exc
    if not isinstance(data, dict):
        raise SnapshotError(f"Snapshot root must be a JSON object: {path}")
    return ActivationSnapshot(path=path, data=data)


def list_activation_snapshots(snapshot_dir: Path, *, limit: int = 0) -> list[ActivationSnapshot]:
    if not snapshot_dir.is_dir():
        return []
    snapshots: list[ActivationSnapshot] = []
    for path in snapshot_dir.glob("*.json"):
        try:
            snapshots.append(load_activation_snapshot(path))
        except SnapshotError:
            continue
    snapshots.sort(key=lambda snapshot: (snapshot.created_at, snapshot.path.name), reverse=True)
    if limit > 0:
        return snapshots[:limit]
    return snapshots


def resolve_activation_snapshot(snapshot_dir: Path, reference: str) -> Path:
    if reference == "latest":
        snapshots = list_activation_snapshots(snapshot_dir, limit=1)
        if snapshots:
            return snapshots[0].path
        raise SnapshotError(f"Snapshot not found: {reference}")

    candidate = Path(reference)
    candidates: list[Path] = []
    if candidate.is_absolute() or candidate.parent != Path("."):
        candidates.append(candidate)
    else:
        candidates.append(snapshot_dir / candidate)
        if candidate.suffix != ".json":
            candidates.append(snapshot_dir / f"{candidate.name}.json")

    for path in candidates:
        if path.is_file():
            return path

    raise SnapshotError(f"Snapshot not found: {reference}")
