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
from collections.abc import Callable, Generator, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from ..config import STATE_DATA_DIR
from . import TUTOR_AUDIO_DIR, TUTOR_VOICE_ID, KnownCharacters, has_hanzi, log_new, recent_new

CHAT_DIR = STATE_DATA_DIR / "tutor_chat"
SESSION_PATH = CHAT_DIR / "session.json"
HISTORY_PATH = CHAT_DIR / "history.jsonl"
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
fit. Keep the conversation going with a question now and then. Be brief."""


def system_prompt(known: KnownCharacters, recent: list[str]) -> str:
    return (
        f"{RULES}\n\nSTUDIED: {''.join(sorted(known.studied))}\n"
        f"UNLOCKED: {''.join(sorted(known.unlocked))}\nRECENT: {''.join(recent) or '-'}\n"
    )


def lines_to_voice(text: str, *, final: bool) -> list[str]:
    """Chinese lines in `text` worth voicing: line 1 and any corrected sentence.

    Only complete lines count unless `final`, so a line is never voiced half-written.
    """
    lines = text.split("\n")
    if not final:
        lines = lines[:-1]
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
            for chunk in stream(text):
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


class Tutor:
    """Owns the Claude process, voice and chat history; one turn at a time."""

    def __init__(self, known: Callable[[], KnownCharacters]) -> None:
        self._known = known
        self._lock = threading.Lock()
        self.speaker = Speaker()
        saved = _read_json(SESSION_PATH)
        saved_model = saved.get("model", "")
        self.model: str = saved_model if saved_model in MODELS else MODELS[0]
        self._chat = self._start(saved.get("session_id"))

    def _start(self, resume: str | None, model: str | None = None) -> ClaudeChat:
        prompt = system_prompt(self._known(), recent_new())
        return ClaudeChat(model or self.model, prompt, resume)

    def _save_session(self) -> None:
        payload = {"model": self.model, "session_id": self._chat.session_id}
        SESSION_PATH.write_text(json.dumps(payload), encoding="utf-8")

    def set_model(self, model: str) -> None:
        if model not in MODELS:
            raise ValueError(f"model must be one of {MODELS}")
        with self._lock:
            if model == self.model:
                return
            fresh = self._start(self._chat.session_id, model)
            self._chat.close()
            self._chat, self.model = fresh, model
            self._save_session()

    def new_chat(self) -> None:
        with self._lock:
            fresh = self._start(None)
            self._chat.close()
            self._chat = fresh
            self._save_session()
            _append(HISTORY_PATH, {"role": "divider"})

    def turn(self, text: str) -> Generator[dict[str, object]]:
        """Stream one turn as events: text deltas, then new characters, then timings."""
        with self._lock:
            if not self._chat.usable:
                self._chat.close()
                self._chat = self._start(self._chat.session_id)
            times = TurnTimes()
            self.speaker.stop()
            _append(HISTORY_PATH, {"role": "user", "text": text})
            reply = ""
            voiced: list[str] = []

            def on_sound(event: str) -> None:
                times.mark(event)

            def voice(final: bool) -> None:
                for line in lines_to_voice(reply, final=final):
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
            self._save_session()
            _append(HISTORY_PATH, {"role": "tutor", "text": reply, "voiced": voiced})

            known = self._known()
            new: dict[str, str] = {}
            for line in voiced:
                for char in known.new_in(line):
                    new.setdefault(char, line)
            log_new(new)
            yield {"t": "new", "chars": list(new)}
            # Wait briefly so the page can show when sound started.
            deadline = time.perf_counter() + _SOUND_WAIT_SECONDS
            while voiced and not times.marks.keys() & {"first_sound", "sound_failed"}:
                if time.perf_counter() > deadline:
                    break
                time.sleep(0.05)
            yield {"t": "done", "times": times.marks}


def history(limit: int = 200) -> list[dict[str, object]]:
    if not HISTORY_PATH.exists():
        return []
    entries = []
    for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            entries.append(json.loads(line))
        except ValueError:
            continue
    return entries


def _append(path: Path, entry: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({**entry, "ts": time.time()}, ensure_ascii=False) + "\n")


def _read_json(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
