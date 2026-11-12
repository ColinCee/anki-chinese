"""Fast chat tutor: an always-running Claude on the user's subscription plus streamed voice.

Claude runs as one long-lived `claude -p` process with no tools, so a turn is a
single model call. The first Chinese line is voiced the moment it is complete,
while the rest of the reply is still streaming.
"""

from __future__ import annotations

import contextlib
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from ..config import STATE_DATA_DIR
from . import TUTOR_AUDIO_DIR, TUTOR_VOICE_ID, KnownCharacters, has_hanzi, recent_new

CHAT_DIR = STATE_DATA_DIR / "tutor_chat"
SESSION_PATH = CHAT_DIR / "session.json"
HISTORY_PATH = CHAT_DIR / "history.jsonl"
MODELS = ("opus", "sonnet")
# Thinking delays the first word by ~1.5 s and adds little to short chat replies.
_NO_THINKING = {"MAX_THINKING_TOKENS": "0"}

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
        self._player = shutil.which("ffplay")
        self._queue: queue.Queue[tuple[str, Callable[[], None]]] = queue.Queue()
        self._current: subprocess.Popen[bytes] | None = None
        threading.Thread(target=self._run, daemon=True).start()

    def say(self, text: str, on_first_sound: Callable[[], None] = lambda: None) -> None:
        self._queue.put((text, on_first_sound))

    def stop(self) -> None:
        """Drop queued clips and cut off the one playing, so a new reply is heard at once."""
        while not self._queue.empty():
            self._queue.get_nowait()
        current = self._current
        if current is not None and current.poll() is None:
            current.kill()

    def _run(self) -> None:
        while True:
            text, on_first_sound = self._queue.get()
            try:
                self._play(text, on_first_sound)
            except Exception as error:  # noqa: BLE001 - a failed clip must not stop later ones
                print(f"audio failed for {text}: {error}", flush=True)

    def _play(self, text: str, on_first_sound: Callable[[], None]) -> None:
        if self._player is None:
            return
        path = self._dir / self._filename(text)
        args = [self._player, "-nodisp", "-autoexit", "-loglevel", "quiet"]
        if path.exists():
            on_first_sound()
            self._current = subprocess.Popen([*args, str(path)], creationflags=_NO_WINDOW)
            self._current.wait()
            return
        stream = getattr(self._provider, "stream_plain_mandarin", None)
        if stream is None:
            return
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
                if not audio:
                    on_first_sound()
                audio.extend(chunk)
                player.stdin.write(chunk)
                player.stdin.flush()
        except OSError:
            return  # stop() killed the player; a cut-off clip is not cached
        finally:
            with contextlib.suppress(OSError):
                player.stdin.close()
            player.wait()
        if audio:
            path.write_bytes(bytes(audio))


class ClaudeChat:
    """One long-lived `claude -p` process; turns are sent over stdin as stream-json."""

    def __init__(self, model: str, prompt: str, resume: str | None) -> None:
        claude = shutil.which("claude")
        if claude is None:
            raise RuntimeError("claude CLI not found on PATH")
        CHAT_DIR.mkdir(parents=True, exist_ok=True)
        prompt_file = CHAT_DIR / "system_prompt.txt"
        prompt_file.write_text(prompt, encoding="utf-8")
        args = [
            claude, "-p", "--model", model, "--effort", "low", "--tools", "",
            "--strict-mcp-config", "--setting-sources", "", "--disable-slash-commands",
            "--system-prompt-file", str(prompt_file),
            "--input-format", "stream-json", "--output-format", "stream-json",
            "--include-partial-messages", "--verbose",
        ]  # fmt: skip
        if resume:
            args += ["--resume", resume]
        self.model = model
        self.session_id = resume
        self._proc = subprocess.Popen(
            args,
            cwd=CHAT_DIR,
            env={**os.environ, **_NO_THINKING},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=_NO_WINDOW,
        )

    def send(self, text: str) -> Iterator[str]:
        """Yield reply text as it streams; ends when the turn is complete."""
        assert self._proc.stdin is not None and self._proc.stdout is not None
        message = {"type": "user", "message": {"role": "user", "content": text}}
        self._proc.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode())
        self._proc.stdin.flush()
        for raw in self._proc.stdout:
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            kind = event.get("type")
            if kind == "stream_event":
                delta = event["event"].get("delta", {})
                if delta.get("type") == "text_delta":
                    yield delta["text"]
            elif kind == "result":
                self.session_id = event.get("session_id", self.session_id)
                if event.get("is_error"):
                    raise RuntimeError(event.get("result") or "Claude returned an error")
                return
        raise RuntimeError("Claude stopped unexpectedly; start a new chat")

    def close(self) -> None:
        if self._proc.stdin:
            self._proc.stdin.close()
        try:
            self._proc.wait(10)
        except subprocess.TimeoutExpired:
            self._proc.kill()


class Tutor:
    """Owns the Claude process, voice and chat history; one turn at a time."""

    def __init__(self, known: Callable[[], KnownCharacters]) -> None:
        self._known = known
        self._lock = threading.Lock()
        self.speaker = Speaker()
        saved = _read_json(SESSION_PATH)
        self.model = saved.get("model", MODELS[0])
        self._chat = self._start(saved.get("session_id"))

    def _start(self, resume: str | None) -> ClaudeChat:
        return ClaudeChat(self.model, system_prompt(self._known(), recent_new()), resume)

    def _save_session(self) -> None:
        payload = {"model": self.model, "session_id": self._chat.session_id}
        SESSION_PATH.write_text(json.dumps(payload), encoding="utf-8")

    def set_model(self, model: str) -> None:
        if model not in MODELS:
            raise ValueError(f"model must be one of {MODELS}")
        with self._lock:
            if model == self.model:
                return
            self._chat.close()
            self.model = model
            self._chat = self._start(self._chat.session_id)
            self._save_session()

    def new_chat(self) -> None:
        with self._lock:
            self._chat.close()
            self._chat = self._start(None)
            _append(HISTORY_PATH, {"role": "divider"})

    def turn(self, text: str) -> Iterator[dict[str, object]]:
        """Stream one turn as events: text deltas, then new characters, then timings."""
        with self._lock:
            times = TurnTimes()
            self.speaker.stop()
            _append(HISTORY_PATH, {"role": "user", "text": text})
            reply = ""
            voiced: list[str] = []

            def voice(final: bool) -> None:
                for line in lines_to_voice(reply, final=final):
                    if line not in voiced:
                        voiced.append(line)
                        times.mark("chinese_ready")
                        self.speaker.say(line, lambda: times.mark("first_sound"))

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

            from . import log_new

            known = self._known()
            new: dict[str, str] = {}
            for line in voiced:
                for char in known.new_in(line):
                    new.setdefault(char, line)
            log_new(new)
            yield {"t": "new", "chars": list(new)}
            deadline = time.perf_counter() + 5
            while voiced and "first_sound" not in times.marks and time.perf_counter() < deadline:
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
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
