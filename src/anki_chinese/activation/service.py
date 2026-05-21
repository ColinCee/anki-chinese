"""Backend-neutral activation planning and execution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from ..config import MODEL_NAME
from ..songs import is_cjk


@dataclass(frozen=True)
class LiveNoteCards:
    character: str
    note_ids: tuple[int, ...]
    card_ids: tuple[int, ...]


@dataclass(frozen=True)
class ActivationPreview:
    requested_chars: tuple[str, ...]
    found_chars: tuple[str, ...]
    missing_chars: tuple[str, ...]
    already_active_chars: tuple[str, ...]
    note_ids: tuple[int, ...]
    card_ids: tuple[int, ...]
    suspended_card_ids: tuple[int, ...]

    @property
    def will_change(self) -> bool:
        return bool(self.suspended_card_ids)


@dataclass(frozen=True)
class ActivationResult:
    preview: ActivationPreview
    snapshot_path: Path | None


@dataclass(frozen=True)
class ResuspendPreview:
    tag: str
    notes: tuple[LiveNoteCards, ...]
    already_suspended_card_ids: tuple[int, ...]
    cards_to_suspend: tuple[int, ...]

    @property
    def found_chars(self) -> tuple[str, ...]:
        return tuple(note.character for note in self.notes)

    @property
    def note_ids(self) -> tuple[int, ...]:
        return tuple(
            sorted({note_id for note in self.notes for note_id in note.note_ids})
        )

    @property
    def card_ids(self) -> tuple[int, ...]:
        return tuple(
            sorted({card_id for note in self.notes for card_id in note.card_ids})
        )

    @property
    def note_ids_to_suspend(self) -> tuple[int, ...]:
        cards_to_suspend = set(self.cards_to_suspend)
        return tuple(
            sorted(
                {
                    note_id
                    for note in self.notes
                    for note_id in note.note_ids
                    if any(card_id in cards_to_suspend for card_id in note.card_ids)
                }
            )
        )

    @property
    def will_change_cards(self) -> bool:
        return bool(self.cards_to_suspend)


@dataclass(frozen=True)
class ResuspendResult:
    preview: ResuspendPreview
    snapshot_path: Path | None


class AnkiClient(Protocol):
    def find_notes_by_chars(self, chars: list[str]) -> dict[str, LiveNoteCards]:
        """Return note/card IDs for exact Hanzi field matches."""
        ...

    def suspended_card_ids(self, card_ids: list[int]) -> set[int]:
        """Return the subset of card IDs that are currently suspended."""
        ...

    def unsuspend_cards(self, card_ids: list[int]) -> None:
        """Unsuspend the supplied live Anki card IDs."""
        ...

    def add_tags(self, note_ids: list[int], tag: str) -> None:
        """Add a tag to the supplied live Anki note IDs."""
        ...


class ActiveStateClient(Protocol):
    def find_active_characters(self) -> set[str]:
        """Return characters with at least one unsuspended live card."""
        ...

    def find_all_deck_info(self) -> tuple[list[str], set[str]]:
        """Return deck order and all character notes in the live model."""
        ...


class ResuspendClient(Protocol):
    def find_notes_by_tag(self, tag: str) -> dict[str, LiveNoteCards]:
        """Return note/card IDs for notes matching a tag."""
        ...

    def suspended_card_ids(self, card_ids: list[int]) -> set[int]:
        """Return the subset of card IDs that are currently suspended."""
        ...

    def suspend_cards(self, card_ids: list[int]) -> None:
        """Suspend the supplied live Anki card IDs."""
        ...

    def remove_tags(self, note_ids: list[int], tag: str) -> None:
        """Remove a tag from the supplied live Anki note IDs."""
        ...


def normalize_character_args(values: list[str]) -> list[str]:
    """Normalize CLI character arguments while preserving first-seen order."""
    chars: list[str] = []
    seen: set[str] = set()
    for value in values:
        for char in value:
            if not is_cjk(char) or char in seen:
                continue
            chars.append(char)
            seen.add(char)
    return chars


def preview_activation(client: AnkiClient, chars: list[str]) -> ActivationPreview:
    requested = tuple(normalize_character_args(chars))
    note_map = client.find_notes_by_chars(list(requested)) if requested else {}

    found_chars = tuple(char for char in requested if char in note_map)
    missing_chars = tuple(char for char in requested if char not in note_map)
    card_ids = tuple(
        card_id
        for char in found_chars
        for card_id in note_map[char].card_ids
    )
    suspended = tuple(sorted(client.suspended_card_ids(list(card_ids)))) if card_ids else ()
    suspended_set = set(suspended)
    already_active = tuple(
        char
        for char in found_chars
        if not any(card_id in suspended_set for card_id in note_map[char].card_ids)
    )
    note_ids = tuple(
        sorted(
            {
                note_id
                for char in found_chars
                for note_id in note_map[char].note_ids
                if any(card_id in suspended_set for card_id in note_map[char].card_ids)
            }
        )
    )

    return ActivationPreview(
        requested_chars=requested,
        found_chars=found_chars,
        missing_chars=missing_chars,
        already_active_chars=already_active,
        note_ids=note_ids,
        card_ids=card_ids,
        suspended_card_ids=suspended,
    )


def write_activation_undo_snapshot(
    preview: ActivationPreview,
    snapshot_dir: Path,
    *,
    tag: str,
    operation: str = "activate-chars",
    model_name: str = MODEL_NAME,
) -> Path:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(UTC).replace(microsecond=0)
    timestamp = created_at.strftime("%Y%m%d-%H%M%S")
    path = snapshot_dir / f"activation-{timestamp}.json"
    counter = 2
    while path.exists():
        path = snapshot_dir / f"activation-{timestamp}-{counter}.json"
        counter += 1

    data = {
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "operation": operation,
        "model_name": model_name,
        "requested_chars": list(preview.requested_chars),
        "found_chars": list(preview.found_chars),
        "missing_chars": list(preview.missing_chars),
        "already_active_chars": list(preview.already_active_chars),
        "note_ids": list(preview.note_ids),
        "card_ids": list(preview.card_ids),
        "pre_change_suspended_card_ids": list(preview.suspended_card_ids),
        "tag": tag,
    }
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def activate_characters(
    client: AnkiClient,
    chars: list[str],
    *,
    tag: str = "",
    dry_run: bool = False,
    snapshot_dir: Path | None = None,
    operation: str = "activate-chars",
    model_name: str = MODEL_NAME,
) -> ActivationResult:
    preview = preview_activation(client, chars)
    if dry_run or not preview.suspended_card_ids:
        return ActivationResult(preview=preview, snapshot_path=None)
    if snapshot_dir is None:
        raise ValueError("snapshot_dir is required before mutating live Anki cards")

    snapshot_path = write_activation_undo_snapshot(
        preview,
        snapshot_dir,
        tag=tag,
        operation=operation,
        model_name=model_name,
    )
    client.unsuspend_cards(list(preview.suspended_card_ids))
    if tag and preview.note_ids:
        client.add_tags(list(preview.note_ids), tag)
    return ActivationResult(preview=preview, snapshot_path=snapshot_path)


def preview_tag_resuspension(client: ResuspendClient, tag: str) -> ResuspendPreview:
    normalized_tag = tag.strip()
    note_map = client.find_notes_by_tag(normalized_tag) if normalized_tag else {}
    notes = tuple(note_map[char] for char in sorted(note_map))
    card_ids = sorted({card_id for note in notes for card_id in note.card_ids})
    suspended = (
        tuple(sorted(client.suspended_card_ids(card_ids)))
        if card_ids
        else ()
    )
    suspended_set = set(suspended)
    cards_to_suspend = tuple(
        card_id for card_id in card_ids if card_id not in suspended_set
    )
    return ResuspendPreview(
        tag=normalized_tag,
        notes=notes,
        already_suspended_card_ids=suspended,
        cards_to_suspend=cards_to_suspend,
    )


def write_resuspend_undo_snapshot(
    preview: ResuspendPreview,
    snapshot_dir: Path,
    *,
    remove_tag: bool,
) -> Path:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(UTC).replace(microsecond=0)
    timestamp = created_at.strftime("%Y%m%d-%H%M%S")
    path = snapshot_dir / f"resuspend-{timestamp}.json"
    counter = 2
    while path.exists():
        path = snapshot_dir / f"resuspend-{timestamp}-{counter}.json"
        counter += 1

    data = {
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "operation": "resuspend-tagged-cards",
        "tag": preview.tag,
        "remove_tag": remove_tag,
        "found_chars": list(preview.found_chars),
        "note_ids": list(preview.note_ids),
        "card_ids": list(preview.card_ids),
        "pre_change_suspended_card_ids": list(preview.already_suspended_card_ids),
        "card_ids_to_suspend": list(preview.cards_to_suspend),
        "note_ids_to_suspend": list(preview.note_ids_to_suspend),
        "characters": [
            {
                "character": note.character,
                "note_ids": list(note.note_ids),
                "card_ids": list(note.card_ids),
            }
            for note in preview.notes
        ],
    }
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def resuspend_tagged_cards(
    client: ResuspendClient,
    tag: str,
    *,
    dry_run: bool = False,
    remove_tag: bool = True,
    snapshot_dir: Path,
) -> ResuspendResult:
    preview = preview_tag_resuspension(client, tag)
    should_remove_tag = remove_tag and bool(preview.note_ids)
    if dry_run or not (preview.cards_to_suspend or should_remove_tag):
        return ResuspendResult(preview=preview, snapshot_path=None)

    snapshot_path = write_resuspend_undo_snapshot(
        preview,
        snapshot_dir,
        remove_tag=remove_tag,
    )
    if preview.cards_to_suspend:
        client.suspend_cards(list(preview.cards_to_suspend))
    if should_remove_tag:
        client.remove_tags(list(preview.note_ids), preview.tag)
    return ResuspendResult(preview=preview, snapshot_path=snapshot_path)
