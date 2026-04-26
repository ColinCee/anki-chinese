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


def test_ankiconnect_error_is_raised_for_api_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout: int = 10):  # noqa: ANN001, ARG001
        return FakeResponse({"result": None, "error": "bad query"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = AnkiConnectClient(url="http://anki.test")

    with pytest.raises(AnkiConnectError, match="bad query"):
        client.suspended_card_ids([1])
