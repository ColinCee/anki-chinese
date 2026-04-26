"""Backend-neutral activation planning and execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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


def activate_characters(
    client: AnkiClient,
    chars: list[str],
    *,
    tag: str = "",
    dry_run: bool = False,
) -> ActivationPreview:
    preview = preview_activation(client, chars)
    if dry_run or not preview.suspended_card_ids:
        return preview

    client.unsuspend_cards(list(preview.suspended_card_ids))
    if tag and preview.note_ids:
        client.add_tags(list(preview.note_ids), tag)
    return preview
