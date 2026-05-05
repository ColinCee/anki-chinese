"""AnkiConnect client for live Anki collection updates."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from ..config import ANKICONNECT_URL, MODEL_NAME
from .service import LiveNoteCards


class AnkiConnectError(RuntimeError):
    """Raised when AnkiConnect is unavailable or returns an error."""


class AnkiConnectClient:
    def __init__(
        self,
        *,
        url: str = ANKICONNECT_URL,
        api_key: str = "",
        model_name: str = MODEL_NAME,
        field_name: str = "Hanzi",
    ) -> None:
        self.url = url
        self.api_key = api_key
        self.model_name = model_name
        self.field_name = field_name

    def _invoke(self, action: str, params: dict[str, Any] | None = None) -> Any:
        payload: dict[str, Any] = {
            "action": action,
            "version": 6,
            "params": params or {},
        }
        if self.api_key:
            payload["key"] = self.api_key

        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as error:
            raise AnkiConnectError(
                f"AnkiConnect is not available at {self.url}. "
                "Open Anki with the AnkiConnect add-on installed, then retry."
            ) from error

        if not isinstance(body, dict) or "error" not in body or "result" not in body:
            raise AnkiConnectError("AnkiConnect returned an unexpected response shape.")
        if body["error"] is not None:
            raise AnkiConnectError(str(body["error"]))
        return body["result"]

    def _find_note_ids(self, char: str) -> list[int]:
        query = f'note:"{self.model_name}" {self.field_name}:{char}'
        result = self._invoke("findNotes", {"query": query})
        if not isinstance(result, list):
            raise AnkiConnectError("findNotes returned an unexpected response shape.")
        return [int(note_id) for note_id in result]

    def _find_all_model_note_ids(self) -> list[int]:
        result = self._invoke("findNotes", {"query": f'note:"{self.model_name}"'})
        if not isinstance(result, list):
            raise AnkiConnectError("findNotes returned an unexpected response shape.")
        return [int(note_id) for note_id in result]

    def _notes_info(self, note_ids: list[int]) -> list[dict[str, Any]]:
        infos = self._invoke("notesInfo", {"notes": note_ids})
        if not isinstance(infos, list):
            raise AnkiConnectError("notesInfo returned an unexpected response shape.")
        return [info for info in infos if isinstance(info, dict)]

    def _extract_field_hanzi(self, raw: str) -> str:
        if "<img" in raw:
            match = re.search(r'src="([0-9a-fA-F]+)\.gif"', raw)
            if match:
                return chr(int(match.group(1), 16))
        return re.sub(r"<[^>]+>", "", raw).strip()

    def _info_character(self, info: dict[str, Any]) -> str:
        fields = info.get("fields", {})
        if not isinstance(fields, dict):
            return ""
        field = fields.get(self.field_name, {})
        value = field.get("value", "") if isinstance(field, dict) else ""
        return self._extract_field_hanzi(value)

    def _collect_exact_infos(
        self,
        chars: set[str],
        infos: list[dict[str, Any]],
    ) -> dict[str, LiveNoteCards]:
        found: dict[str, LiveNoteCards] = {}
        for info in infos:
            char = self._info_character(info)
            if char not in chars:
                continue
            existing = found.get(char)
            note_ids = tuple([*(existing.note_ids if existing else ()), int(info["noteId"])])
            card_ids = tuple(
                [
                    *(existing.card_ids if existing else ()),
                    *(int(card_id) for card_id in info.get("cards", [])),
                ]
            )
            found[char] = LiveNoteCards(character=char, note_ids=note_ids, card_ids=card_ids)
        return found

    def find_notes_by_chars(self, chars: list[str]) -> dict[str, LiveNoteCards]:
        found: dict[str, LiveNoteCards] = {}
        for char in chars:
            note_ids = self._find_note_ids(char)
            if not note_ids:
                continue

            found.update(self._collect_exact_infos({char}, self._notes_info(note_ids)))

        missing = set(chars) - set(found)
        if missing:
            all_note_ids = self._find_all_model_note_ids()
            found.update(self._collect_exact_infos(missing, self._notes_info(all_note_ids)))
        return found

    def suspended_card_ids(self, card_ids: list[int]) -> set[int]:
        if not card_ids:
            return set()
        result = self._invoke("areSuspended", {"cards": card_ids})
        if not isinstance(result, list):
            raise AnkiConnectError("areSuspended returned an unexpected response shape.")
        return {card_id for card_id, suspended in zip(card_ids, result, strict=True) if suspended}

    def unsuspend_cards(self, card_ids: list[int]) -> None:
        if card_ids:
            self._invoke("unsuspend", {"cards": card_ids})

    def add_tags(self, note_ids: list[int], tag: str) -> None:
        if note_ids and tag:
            self._invoke("addTags", {"notes": note_ids, "tags": tag})

    def find_studied_characters(self) -> set[str]:
        """Return characters that have actually been studied (at least one review).

        Uses ``-is:new -is:suspended`` to find cards the user has seen.
        A character counts as studied if *any* of its cards match.
        """
        query = f'note:"{self.model_name}" -is:new -is:suspended'
        note_ids = self._invoke("findNotes", {"query": query})
        if not isinstance(note_ids, list) or not note_ids:
            return set()
        infos = self._notes_info(note_ids)
        return {self._info_character(info) for info in infos} - {""}

    def find_all_deck_info(self) -> tuple[list[str], set[str]]:
        """Return (deck_order, deck_chars) from the live Anki collection.

        ``deck_order`` is sorted by HeisigNum field (RSH order).
        ``deck_chars`` is the complete set of characters in the model.
        """
        note_ids = self._find_all_model_note_ids()
        if not note_ids:
            return [], set()
        infos = self._notes_info(note_ids)

        entries: list[tuple[int, str]] = []
        for info in infos:
            char = self._info_character(info)
            if not char:
                continue
            fields = info.get("fields", {})
            heisig_field = fields.get("HeisigNum", {})
            heisig_raw = heisig_field.get("value", "0") if isinstance(heisig_field, dict) else "0"
            try:
                heisig_num = int(re.sub(r"<[^>]+>", "", heisig_raw).strip() or "0")
            except ValueError:
                heisig_num = 0
            entries.append((heisig_num, char))

        entries.sort(key=lambda e: e[0])
        deck_order = [char for _, char in entries]
        deck_chars = set(deck_order)
        return deck_order, deck_chars
