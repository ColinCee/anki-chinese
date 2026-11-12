import io
import json

import pytest

from anki_chinese.audio import minimax as tts
from anki_chinese.audio.errors import TTSError
from anki_chinese.audio.rate_limit import NoOpRateLimiter
from anki_chinese.tutor import KnownCharacters
from anki_chinese.tutor.chat import lines_to_voice, system_prompt


def test_lines_to_voice_waits_for_a_complete_first_line() -> None:
    assert lines_to_voice("你今天怎么", final=False) == []
    assert lines_to_voice("你今天怎么样？\nHow are", final=False) == ["你今天怎么样？"]


def test_lines_to_voice_adds_corrected_sentence_and_skips_english() -> None:
    reply = (
        "**辛苦了！**\nYou worked hard!\nNew: 辛 (xīn) hard\n**Corrected:** 我今天很累。\n1. note"
    )

    assert lines_to_voice(reply, final=True) == ["辛苦了！", "我今天很累。"]
    assert lines_to_voice("Hello!\nEnglish only", final=True) == []


def test_system_prompt_lists_known_and_recent_characters() -> None:
    known = KnownCharacters(
        studied=frozenset("好你"), unlocked=frozenset("学"), source="t", updated="t"
    )

    prompt = system_prompt(known, ["处"])

    assert "STUDIED: 你好" in prompt
    assert "UNLOCKED: 学" in prompt
    assert "RECENT: 处" in prompt


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _sse(*events: dict) -> _Response:
    return _Response(b"".join(b"data: " + json.dumps(e).encode() + b"\n\n" for e in events))


def _provider(monkeypatch, response: _Response) -> tts.MiniMaxTTSProvider:
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    monkeypatch.setattr(tts, "urlopen", lambda request, timeout: response)
    return tts.MiniMaxTTSProvider(rate_limiter=NoOpRateLimiter())


def test_stream_plain_mandarin_yields_only_new_chunks(monkeypatch) -> None:
    ok = {"status_code": 0, "status_msg": ""}
    response = _sse(
        {"data": {"status": 1, "audio": "4944"}, "base_resp": ok},
        {"data": {"status": 1, "audio": "33"}, "base_resp": ok},
        {"data": {"status": 2, "audio": "49443300"}, "base_resp": ok},
    )

    chunks = list(_provider(monkeypatch, response).stream_plain_mandarin("你好"))

    assert chunks == [b"ID", b"3"]


def test_stream_plain_mandarin_raises_on_error_status(monkeypatch) -> None:
    response = _sse({"base_resp": {"status_code": 1004, "status_msg": "auth failed"}})

    with pytest.raises(TTSError, match="auth failed"):
        list(_provider(monkeypatch, response).stream_plain_mandarin("你好"))


def test_stream_plain_mandarin_raises_on_plain_json_error_body(monkeypatch) -> None:
    body = json.dumps({"base_resp": {"status_code": 1004, "status_msg": "bad key"}}).encode()

    with pytest.raises(TTSError, match="bad key"):
        list(_provider(monkeypatch, _Response(body)).stream_plain_mandarin("你好"))


def test_stream_plain_mandarin_rejects_a_clip_cut_short(monkeypatch) -> None:
    ok = {"status_code": 0, "status_msg": ""}
    response = _Response(
        b"data: [DONE]\n\n"
        + b"data: "
        + json.dumps({"data": {"status": 1, "audio": "4944"}, "base_resp": ok}).encode()
    )

    with pytest.raises(TTSError, match="before the clip was complete"):
        list(_provider(monkeypatch, response).stream_plain_mandarin("你好"))


@pytest.mark.parametrize(
    ("method", "host", "origin", "content_type", "allowed"),
    [
        ("GET", "127.0.0.1:8790", None, None, True),
        ("POST", "localhost:8790", "http://localhost:8790", "application/json", True),
        ("POST", "127.0.0.1:8790", None, "text/plain", False),
        ("POST", "127.0.0.1:8790", "https://evil.example", "application/json", False),
        ("GET", "evil.example:8790", None, None, False),
    ],
)
def test_request_allowed_only_from_the_page(method, host, origin, content_type, allowed) -> None:
    from anki_chinese.tutor.server import request_allowed

    result = request_allowed(
        method=method, host=host, origin=origin, content_type=content_type, port=8790
    )

    assert result is allowed


_FAKE_CLAUDE = """
import json, sys
for line in sys.stdin:
    text = json.loads(line)["message"]["content"]
    for part in ("reply ", "to ", text):
        event = {"type": "text_delta", "text": part}
        print(json.dumps({"type": "stream_event", "event": {"delta": event}}), flush=True)
    print(json.dumps({"type": "result", "session_id": "s1"}), flush=True)
"""


def test_abandoned_turn_marks_the_chat_unusable(tmp_path, monkeypatch) -> None:
    import sys

    from anki_chinese.tutor import chat

    monkeypatch.setattr(chat, "CHAT_DIR", tmp_path)
    command = [sys.executable, "-c", _FAKE_CLAUDE]

    first = chat.ClaudeChat("opus", "", None, command=command)
    turn = first.send("a")
    assert next(turn) == "reply "
    turn.close()
    assert not first.usable
    first.close()

    second = chat.ClaudeChat("opus", "", None, command=command)
    assert "".join(second.send("b")) == "reply to b"
    assert second.usable and second.session_id == "s1"
    second.close()


def test_chat_store_keeps_chats_apart_and_survives_reload(tmp_path) -> None:
    from anki_chinese.tutor.chat import ChatStore

    store = ChatStore(tmp_path)
    first = store.current
    store.chats[first].update(title="first", session_id="s1", updated=1.0)
    second = store.create()
    store.chats[second].update(updated=2.0)
    store.save()

    reloaded = ChatStore(tmp_path)

    assert reloaded.current == second
    assert [row["id"] for row in reloaded.snapshot()["chats"]] == [second, first]
    assert reloaded.chats[first]["session_id"] == "s1"
    assert reloaded.history_path(first) != reloaded.history_path(second)


def test_chat_store_survives_a_damaged_index(tmp_path) -> None:
    from anki_chinese.tutor.chat import ChatStore

    damaged = {"current": ["x"], "chats": {"a": "oops", "b": {"session_id": 3}}}
    (tmp_path / "chats.json").write_text(json.dumps(damaged), encoding="utf-8")

    store = ChatStore(tmp_path)

    assert set(store.chats) == {"b", store.current}
    assert store.chats["b"] == {"title": "New chat", "session_id": None, "updated": 0.0}
    assert store.snapshot()["current"] == store.current


def test_history_folds_late_timings_into_the_reply(tmp_path) -> None:
    from anki_chinese.tutor.chat import ChatStore

    store = ChatStore(tmp_path)
    path = store.history_path(store.current)
    path.parent.mkdir(parents=True)
    lines = [
        {"role": "user", "text": "你好"},
        {"role": "tutor", "text": "你好！"},
        {"role": "times", "times": {"first_sound": 2.1}},
    ]
    path.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")

    history = store.history(store.current)

    assert [h["role"] for h in history] == ["user", "tutor"]
    assert history[1]["times"] == {"first_sound": 2.1}
