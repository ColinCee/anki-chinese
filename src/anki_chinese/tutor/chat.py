"""Fast chat tutor: an always-running Claude on the user's subscription plus streamed voice.

Claude runs as one long-lived `claude -p` process with no tools, so a turn is a
single model call. The first Chinese line is voiced the moment it is complete,
while the rest of the reply is still streaming.
"""

from __future__ import annotations

import collections
import contextlib
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid
from collections.abc import Callable, Generator, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import STATE_DATA_DIR
from . import (
    TUTOR_AUDIO_DIR,
    TUTOR_VOICE_ID,
    KnownCharacters,
    _write_atomic,
    has_hanzi,
    log_new,
    recent_new,
)

CHAT_DIR = STATE_DATA_DIR / "tutor_chat"
MODELS = ("opus", "sonnet")
# Thinking delays the first word by ~1.5 s and adds little to short chat replies.
_NO_THINKING = {"MAX_THINKING_TOKENS": "0"}
_REPLY_STALL_SECONDS = 90
_SOUND_WAIT_SECONDS = 3

_CORRECTED = re.compile(r"^\W*corrected\W*:?\W*(.+)$", re.IGNORECASE)
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

RULES = """You are a Mandarin chat tutor in a voice chat. Reply format, exactly:
Line 1: your reply in Chinese only: one or two short, natural sentences. No pinyin, no markdown.
Line 2: the English of line 1.
Then, for each character in line 1 that is not in STUDIED or UNLOCKED: "New: 字 (pinyin) meaning".
If the user wrote Chinese with mistakes, add a line "Corrected: <their full sentence, corrected>"
and then short numbered notes in English. If their Chinese was fine, say nothing about it.

Write the most natural sentence first. Never bend it to avoid a character the user has not
studied: use it and list it as New. New characters only when they fit the conversation:
usually 1-2 per reply, sometimes more, none when nothing fits. Reuse RECENT characters when they
fit. Keep the conversation going with a question now and then. Be brief.

Reply straight away: this is a live voice chat and every second of delay is felt.
Keep any private reasoning to a sentence or two."""


def system_prompt(known: KnownCharacters, recent: list[str]) -> str:
    return (
        f"{RULES}\n\nSTUDIED: {''.join(sorted(known.studied))}\n"
        f"UNLOCKED: {''.join(sorted(known.unlocked))}\nRECENT: {''.join(recent) or '-'}\n"
    )


def lines_to_voice(text: str, *, final: bool, read_all: bool = False) -> list[str]:
    """Lines in `text` worth voicing: line 1 and any corrected sentence, or every line.

    Only complete lines count unless `final`, so a line is never voiced half-written.
    """
    lines = text.split("\n")
    if not final:
        lines = lines[:-1]
    if read_all:
        spoken = (_clean(line) for line in lines)
        return list(dict.fromkeys(line for line in spoken if re.search(r"\w", line)))
    found: list[str] = []
    first = next((line for line in lines if line.strip()), None)
    if first is not None and has_hanzi(first):
        found.append(_clean(first))
    for line in lines:
        match = _CORRECTED.match(line.strip())
        if match and has_hanzi(match.group(1)):
            found.append(_clean(match.group(1)))
    return list(dict.fromkeys(found))


def _clean(line: str) -> str:
    return line.replace("*", "").replace("`", "").strip(" \"'“”")


@dataclass
class TurnTimes:
    started: float = field(default_factory=time.perf_counter)
    marks: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str) -> None:
        self.marks.setdefault(name, round(time.perf_counter() - self.started, 2))


class Speaker:
    """Plays clips one after another; streams new clips from MiniMax as they arrive."""

    def __init__(self, voice_id: str = TUTOR_VOICE_ID) -> None:
        from ..audio import build_tts_provider
        from ..audio.files import preview_mandarin_filename

        self._filename = preview_mandarin_filename
        self._dir = TUTOR_AUDIO_DIR / voice_id
        self._dir.mkdir(parents=True, exist_ok=True)
        self._provider = build_tts_provider(
            generated_audio_dir=self._dir, provider_name="minimax", mandarin_voice_id=voice_id
        )
        self.player = shutil.which("ffplay")
        self._queue: queue.Queue[tuple[int, str, Callable[[str], None]]] = queue.Queue()
        # stop() bumps the generation; anything queued or playing from an older one is dropped.
        self._generation = 0
        self._current: subprocess.Popen[bytes] | None = None
        threading.Thread(target=self._run, daemon=True).start()

    def say(self, text: str, on_event: Callable[[str], None] = lambda _event: None) -> None:
        """Queue a clip; `on_event` gets "first_sound" or "sound_failed"."""
        self._queue.put((self._generation, text, on_event))

    def stop(self) -> None:
        self._generation += 1
        current = self._current
        if current is not None and current.poll() is None:
            current.kill()

    def _run(self) -> None:
        while True:
            generation, text, on_event = self._queue.get()
            if generation != self._generation:
                continue
            try:
                self._play(generation, text, on_event)
            except Exception as error:  # noqa: BLE001 - a failed clip must not stop later ones
                print(f"audio failed for {text}: {error}", flush=True)
                on_event("sound_failed")

    def _play(self, generation: int, text: str, on_event: Callable[[str], None]) -> None:
        if self.player is None:
            raise RuntimeError("ffplay not found on PATH")
        path = self._dir / self._filename(text)
        args = [self.player, "-nodisp", "-autoexit", "-loglevel", "quiet"]
        if path.exists():
            on_event("first_sound")
            self._current = subprocess.Popen([*args, str(path)], creationflags=_NO_WINDOW)
            self._current.wait()
            return
        stream = getattr(self._provider, "stream_plain_mandarin", None)
        if stream is None:
            raise RuntimeError("the TTS provider cannot stream")
        # Small probe so ffplay starts on the first chunk instead of buffering.
        live = [
            *args,
            "-probesize",
            "32",
            "-analyzeduration",
            "0",
            "-fflags",
            "nobuffer",
            "-i",
            "-",
        ]
        player = subprocess.Popen(live, stdin=subprocess.PIPE, creationflags=_NO_WINDOW)
        self._current = player
        audio = bytearray()
        assert player.stdin is not None
        try:
            # Pure Chinese lines get the Chinese boost; English or mixed lines need auto.
            boost = "Chinese" if has_hanzi(text) and not re.search("[A-Za-z]", text) else "auto"
            for chunk in stream(text, language_boost=boost):
                if generation != self._generation:
                    return  # cut off by stop(); stop paying for the rest
                if not audio:
                    on_event("first_sound")
                audio.extend(chunk)
                player.stdin.write(chunk)
                player.stdin.flush()
        except OSError:
            return  # stop() killed the player mid-clip
        finally:
            with contextlib.suppress(OSError):
                player.stdin.close()
            player.wait()
        # The stream raises unless MiniMax confirmed the clip, so this is never partial.
        path.write_bytes(bytes(audio))


class ClaudeChat:
    """One long-lived `claude -p` process; turns are sent over stdin as stream-json."""

    def __init__(
        self, model: str, prompt: str, resume: str | None, command: list[str] | None = None
    ) -> None:
        CHAT_DIR.mkdir(parents=True, exist_ok=True)
        if command is None:
            claude = shutil.which("claude")
            if claude is None:
                raise RuntimeError("claude CLI not found on PATH")
            prompt_file = CHAT_DIR / "system_prompt.txt"
            prompt_file.write_text(prompt, encoding="utf-8")
            command = [
                claude, "-p", "--model", model, "--effort", "low", "--tools", "",
                "--strict-mcp-config", "--setting-sources", "", "--disable-slash-commands",
                "--system-prompt-file", str(prompt_file),
                "--input-format", "stream-json", "--output-format", "stream-json",
                "--include-partial-messages", "--verbose",
            ]  # fmt: skip
            if resume:
                command += ["--resume", resume]
        self.model = model
        self.session_id = resume
        # A turn that did not reach its `result` leaves events in the pipe; the
        # owner must replace this process rather than read them as the next reply.
        self.in_turn = False
        self._proc = subprocess.Popen(
            command,
            cwd=CHAT_DIR,
            env={**os.environ, **_NO_THINKING},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=_NO_WINDOW,
        )
        self._events: queue.Queue[dict[str, object] | None] = queue.Queue()
        self._stderr: collections.deque[str] = collections.deque(maxlen=5)
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    @property
    def usable(self) -> bool:
        return not self.in_turn and self._proc.poll() is None

    def _read_stdout(self) -> None:
        assert self._proc.stdout is not None
        for raw in self._proc.stdout:
            with contextlib.suppress(ValueError):
                self._events.put(json.loads(raw))
        self._events.put(None)

    def _read_stderr(self) -> None:
        assert self._proc.stderr is not None
        for raw in self._proc.stderr:
            line = raw.decode("utf-8", errors="replace").strip()
            if line:
                self._stderr.append(line)

    def _failure(self, what: str) -> RuntimeError:
        detail = " | ".join(self._stderr)
        return RuntimeError(f"{what}{': ' + detail if detail else ''}")

    def send(self, text: str) -> Iterator[str]:
        """Yield reply text as it streams; ends when the turn is complete."""
        assert self._proc.stdin is not None
        self.in_turn = True
        message = {"type": "user", "message": {"role": "user", "content": text}}
        try:
            self._proc.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode())
            self._proc.stdin.flush()
        except OSError as error:
            raise self._failure("Claude is not running") from error
        while True:
            try:
                event = self._events.get(timeout=_REPLY_STALL_SECONDS)
            except queue.Empty as error:
                self._proc.kill()
                raise self._failure("Claude stopped responding") from error
            if event is None:
                raise self._failure("Claude stopped unexpectedly")
            kind = event.get("type")
            if kind == "stream_event":
                inner = event.get("event")
                delta = inner.get("delta", {}) if isinstance(inner, dict) else {}
                if isinstance(delta, dict) and delta.get("type") == "text_delta":
                    yield str(delta.get("text", ""))
            elif kind == "result":
                self.in_turn = False
                self.session_id = str(event.get("session_id") or self.session_id)
                if event.get("is_error"):
                    raise RuntimeError(str(event.get("result") or "Claude returned an error"))
                return

    def close(self) -> None:
        with contextlib.suppress(OSError):
            if self._proc.stdin:
                self._proc.stdin.close()
        try:
            self._proc.wait(5)
        except subprocess.TimeoutExpired:
            self._proc.kill()


class ChatStore:
    """Saved chats: an index (title, Claude session, last use) plus one history file each.

    Thread-safe: the page polls state while a turn is running.
    """

    def __init__(self, root: Path = CHAT_DIR) -> None:
        self._index_path = root / "chats.json"
        self._dir = root / "chats"
        self._lock = threading.RLock()
        data = _read_json(self._index_path)
        raw_chats = data.get("chats")
        self.chats: dict[str, dict[str, Any]] = {}
        if isinstance(raw_chats, dict):
            for key, value in raw_chats.items():
                if isinstance(key, str) and isinstance(value, dict):
                    session = value.get("session_id")
                    self.chats[key] = {
                        "title": str(value.get("title") or "New chat"),
                        "session_id": session if isinstance(session, str) else None,
                        "updated": float(value.get("updated") or 0),
                    }
        model = data.get("model")
        self.model: str = model if isinstance(model, str) and model in MODELS else MODELS[0]
        current = data.get("current")
        self.current: str = (
            current if isinstance(current, str) and current in self.chats else self.create()
        )

    def create(self) -> str:
        with self._lock:
            chat_id = uuid.uuid4().hex[:12]
            self.chats[chat_id] = {"title": "New chat", "session_id": None, "updated": time.time()}
            self.current = chat_id
            self.save()
            return chat_id

    def save(self) -> None:
        with self._lock:
            payload = {"model": self.model, "current": self.current, "chats": self.chats}
            _write_atomic(self._index_path, json.dumps(payload, ensure_ascii=False, indent=1))

    def update(self, chat_id: str, *, first_message: str, session_id: str | None) -> str:
        """Record a finished turn; returns the chat's title."""
        with self._lock:
            entry = self.chats[chat_id]
            if entry["title"] == "New chat":
                entry["title"] = first_message[:40]
            entry.update(session_id=session_id, updated=time.time())
            self.save()
            return entry["title"]

    def is_empty(self, chat_id: str) -> bool:
        return not self.history_path(chat_id).exists()

    def history_path(self, chat_id: str) -> Path:
        return self._dir / f"{chat_id}.jsonl"

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            rows = sorted(self.chats.items(), key=lambda item: item[1]["updated"], reverse=True)
            return {
                "model": self.model,
                "current": self.current,
                "chats": [{"id": key, "title": value["title"]} for key, value in rows],
                "history": self.history(self.current),
            }

    def history(self, chat_id: str, limit: int = 300) -> list[dict[str, Any]]:
        path = self.history_path(chat_id)
        if not path.exists():
            return []
        entries: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict):
                continue
            # Timings are written after the reply itself; fold them back into it.
            if entry.get("role") == "times" and entries and entries[-1].get("role") == "tutor":
                entries[-1]["times"] = entry.get("times")
            else:
                entries.append(entry)
        return entries


class Tutor:
    """Owns the Claude process, voice and saved chats; one turn at a time."""

    def __init__(
        self, known: Callable[[], KnownCharacters], store: ChatStore | None = None
    ) -> None:
        self._known = known
        self._lock = threading.Lock()
        self.speaker = Speaker()
        self.store = store or ChatStore()
        self._chat = self._start(self._session(self.store.current))

    @property
    def model(self) -> str:
        return self.store.model

    def _session(self, chat_id: str) -> str | None:
        return self.store.chats[chat_id].get("session_id")

    def _start(self, resume: str | None, model: str | None = None) -> ClaudeChat:
        prompt = system_prompt(self._known(), recent_new())
        return ClaudeChat(model or self.model, prompt, resume)

    def _switch(self, resume: str | None, model: str | None = None) -> None:
        fresh = self._start(resume, model)
        self._chat.close()
        self._chat = fresh

    def _open(self, chat_id: str) -> None:
        if chat_id == self.store.current:
            return
        self.speaker.stop()
        self._switch(self._session(chat_id))
        self.store.current = chat_id
        self.store.save()

    def replay(self, text: str, *, read_all: bool) -> None:
        """Play a reply again: its first line, or the whole reply line by line."""
        self.speaker.stop()
        lines = lines_to_voice(text, final=True, read_all=read_all) if read_all else [text]
        for line in lines:
            self.speaker.say(line)

    def set_model(self, model: str) -> None:
        if model not in MODELS:
            raise ValueError(f"model must be one of {MODELS}")
        with self._lock:
            if model == self.model:
                return
            self._switch(self._chat.session_id, model)
            self.store.model = model
            self.store.save()

    def new_chat(self) -> None:
        with self._lock:
            self.speaker.stop()
            if self.store.is_empty(self.store.current):
                return  # already on an unused chat
            self._switch(None)
            self.store.create()

    def open_chat(self, chat_id: str) -> None:
        if chat_id not in self.store.chats:
            raise ValueError("no such chat")
        with self._lock:
            self._open(chat_id)

    def turn(
        self, text: str, chat_id: str | None = None, *, read_all: bool = False
    ) -> Generator[dict[str, object]]:
        """Stream one turn in `chat_id` (default: current): text deltas, new characters, timings."""
        if chat_id is not None and chat_id not in self.store.chats:
            raise ValueError("no such chat")
        with self._lock:
            # Another tab may have switched chats; answer in the chat this page shows.
            if chat_id is not None:
                self._open(chat_id)
            chat_id = self.store.current
            if not self._chat.usable:
                self._switch(self._chat.session_id)
            times = TurnTimes()
            self.speaker.stop()
            history_path = self.store.history_path(chat_id)
            _append(history_path, {"role": "user", "text": text})
            reply = ""
            voiced: list[str] = []

            def on_sound(event: str) -> None:
                times.mark(event)

            def voice(final: bool) -> None:
                for line in lines_to_voice(reply, final=final, read_all=read_all):
                    if line not in voiced:
                        voiced.append(line)
                        times.mark("chinese_ready")
                        self.speaker.say(line, on_sound)

            for delta in self._chat.send(text):
                times.mark("first_text")
                reply += delta
                if "\n" in delta:
                    voice(final=False)
                yield {"t": "text", "d": delta}
            voice(final=True)
            times.mark("reply_done")

            # Save before yielding again: the page may already be gone.
            known = self._known()
            new: dict[str, str] = {}
            for line in lines_to_voice(reply, final=True):
                for char in known.new_in(line):
                    new.setdefault(char, line)
            log_new(new)
            _append(history_path, {"role": "tutor", "text": reply, "new": list(new)})
            title = self.store.update(chat_id, first_message=text, session_id=self._chat.session_id)
            yield {"t": "chat", "id": chat_id, "title": title}
            yield {"t": "new", "chars": list(new)}

            deadline = time.perf_counter() + _SOUND_WAIT_SECONDS
            while voiced and not times.marks.keys() & {"first_sound", "sound_failed"}:
                if time.perf_counter() > deadline:
                    break
                time.sleep(0.05)
            marks = dict(times.marks)  # the speaker thread may still add to it
            _append(history_path, {"role": "times", "times": marks})
            yield {"t": "done", "times": marks}


def _append(path: Path, entry: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({**entry, "ts": time.time()}, ensure_ascii=False) + "\n")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
