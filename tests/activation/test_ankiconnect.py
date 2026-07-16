from __future__ import annotations

import json
from typing import Any

import pytest

from anki_chinese.activation import AnkiConnectClient, AnkiConnectError


class FakeResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.body).encode("utf-8")


def test_find_notes_by_chars_filters_exact_hanzi(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[dict[str, Any]] = []

    def fake_urlopen(request, timeout: int = 10):  # noqa: ANN001
        payload = json.loads(request.data.decode("utf-8"))
        requests.append(payload)
        if payload["action"] == "findNotes":
            return FakeResponse({"result": [1, 2], "error": None})
        if payload["action"] == "notesInfo":
            return FakeResponse(
                {
                    "result": [
                        {
                            "noteId": 1,
                            "fields": {"Hanzi": {"value": "水"}},
                            "cards": [10, 11],
                        },
                        {
                            "noteId": 2,
                            "fields": {"Hanzi": {"value": "水面"}},
                            "cards": [20, 21],
                        },
                    ],
                    "error": None,
                }
            )
        raise AssertionError(payload["action"])

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = AnkiConnectClient(url="http://anki.test", model_name="Chinese RSH")

    result = client.find_notes_by_chars(["水"])

    assert result["水"].note_ids == (1,)
    assert result["水"].card_ids == (10, 11)
    assert requests[0]["params"]["query"] == 'note:"Chinese RSH" Hanzi:水'


def test_find_notes_by_tag_and_resuspend_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[dict[str, Any]] = []

    def fake_urlopen(request, timeout: int = 10):  # noqa: ANN001, ARG001
        payload = json.loads(request.data.decode("utf-8"))
        requests.append(payload)
        if payload["action"] == "findNotes":
            return FakeResponse({"result": [1], "error": None})
        if payload["action"] == "notesInfo":
            return FakeResponse(
                {
                    "result": [
                        {
                            "noteId": 1,
                            "fields": {"Hanzi": {"value": "火"}},
                            "cards": [20, 21],
                        },
                    ],
                    "error": None,
                }
            )
        return FakeResponse({"result": None, "error": None})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = AnkiConnectClient(url="http://anki.test", model_name="Chinese RSH")

    result = client.find_notes_by_tag("activated::song::测试歌")
    client.suspend_cards([20, 21])
    client.remove_tags([1], "activated::song::测试歌")

    assert result["火"].note_ids == (1,)
    assert result["火"].card_ids == (20, 21)
    assert requests[0]["params"]["query"] == 'note:"Chinese RSH" tag:"activated::song::测试歌"'
    assert requests[2]["action"] == "suspend"
    assert requests[2]["params"] == {"cards": [20, 21]}
    assert requests[3]["action"] == "removeTags"
    assert requests[3]["params"] == {"notes": [1], "tags": "activated::song::测试歌"}


def test_find_active_characters_uses_any_unsuspended_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, Any]] = []

    def fake_urlopen(request, timeout: int = 10):  # noqa: ANN001, ARG001
        payload = json.loads(request.data.decode("utf-8"))
        requests.append(payload)
        if payload["action"] == "findNotes":
            return FakeResponse({"result": [1, 2, 3], "error": None})
        if payload["action"] == "notesInfo":
            return FakeResponse(
                {
                    "result": [
                        {
                            "noteId": 1,
                            "fields": {"Hanzi": {"value": "水"}},
                            "cards": [10, 11],
                        },
                        {
                            "noteId": 2,
                            "fields": {"Hanzi": {"value": "火"}},
                            "cards": [20, 21],
                        },
                        {
                            "noteId": 3,
                            "fields": {"Hanzi": {"value": "山"}},
                            "cards": [30, 31],
                        },
                    ],
                    "error": None,
                }
            )
        if payload["action"] == "areSuspended":
            assert payload["params"] == {"cards": [10, 11, 20, 21, 30, 31]}
            return FakeResponse(
                {"result": [True, False, True, True, False, False], "error": None}
            )
        raise AssertionError(payload["action"])

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = AnkiConnectClient(url="http://anki.test", model_name="Chinese RSH")

    result = client.find_active_characters()

    assert result == {"水", "山"}
    assert requests[0]["params"]["query"] == 'note:"Chinese RSH"'


def test_find_studied_characters_uses_review_counts_not_suspension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, Any]] = []

    def fake_urlopen(request, timeout: int = 10):  # noqa: ANN001, ARG001
        payload = json.loads(request.data.decode("utf-8"))
        requests.append(payload)
        if payload["action"] == "findCards":
            return FakeResponse({"result": [10, 20, 30], "error": None})
        if payload["action"] == "cardsInfo":
            return FakeResponse(
                {
                    "result": [
                        {"cardId": 10, "note": 1, "reps": 3},
                        {"cardId": 20, "note": 2, "reps": 0},
                        {"cardId": 30, "note": 3, "reps": 2},
                    ],
                    "error": None,
                }
            )
        if payload["action"] == "notesInfo":
            return FakeResponse(
                {
                    "result": [
                        {"noteId": 1, "fields": {"Hanzi": {"value": "水"}}},
                        {"noteId": 3, "fields": {"Hanzi": {"value": "山"}}},
                    ],
                    "error": None,
                }
            )
        raise AssertionError(payload["action"])

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = AnkiConnectClient(url="http://anki.test", model_name="Chinese RSH")

    result = client.find_studied_characters()

    assert result == {"水", "山"}
    assert requests[0]["params"]["query"] == 'note:"Chinese RSH"'


def test_ankiconnect_error_is_raised_for_api_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout: int = 10):  # noqa: ANN001, ARG001
        return FakeResponse({"result": None, "error": "bad query"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = AnkiConnectClient(url="http://anki.test")

    with pytest.raises(AnkiConnectError, match="bad query"):
        client.suspended_card_ids([1])
