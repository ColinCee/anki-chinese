"""Chat tutor: which characters you know, voicing replies, logging new characters.

Imports nothing from the CLI composition root, so a tutor turn starts fast.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .config import BUILD_AUDIO_DIR, MODEL_ID, STATE_DATA_DIR

TUTOR_VOICE_ID = "Chinese_wenrounvxing"
TUTOR_AUDIO_DIR = BUILD_AUDIO_DIR / "tutor"
KNOWN_PATH = STATE_DATA_DIR / "tutor_known.json"
LOG_PATH = STATE_DATA_DIR / "tutor_log.jsonl"
ANKI_COLLECTION_PATH = Path(os.getenv("APPDATA", "")) / "Anki2" / "User 1" / "collection.anki2"

_HANZI = re.compile(r"[㐀-䶿一-鿿\U00020000-\U0002ebef]")
_SUSPENDED_QUEUE = -1


@dataclass(frozen=True)
class KnownCharacters:
    studied: frozenset[str]
    unlocked: frozenset[str]
    source: str
    updated: str

    def new_in(self, text: str) -> list[str]:
        known = self.studied | self.unlocked
        return list(dict.fromkeys(c for c in _HANZI.findall(text) if c not in known))


def extract_hanzi(raw_field: str) -> str:
    # Rare glyphs are stored as <img src="<codepoint hex>.gif">.
    match = re.search(r'src="([0-9a-fA-F]+)\.gif"', raw_field)
    if "<img" in raw_field and match:
        return chr(int(match.group(1), 16))
    return re.sub(r"<[^>]+>", "", raw_field).strip()


def read_collection(path: Path = ANKI_COLLECTION_PATH) -> tuple[set[str], set[str]]:
    # Only used when AnkiConnect is unreachable: an open Anki keeps recent
    # changes in a WAL file this copy would miss.
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "collection.anki2"
        shutil.copyfile(path, copy)
        db = sqlite3.connect(f"file:{copy.as_posix()}?mode=ro", uri=True)
        try:
            rows = db.execute(
                "SELECT n.flds, MAX(c.reps), MAX(c.queue) FROM notes n "
                "JOIN cards c ON c.nid = n.id WHERE n.mid = ? GROUP BY n.id",
                (MODEL_ID,),
            ).fetchall()
        finally:
            db.close()
    studied: set[str] = set()
    unlocked: set[str] = set()
    for fields, reps, queue in rows:
        char = extract_hanzi(fields.split("\x1f", 1)[0])
        if not char:
            continue
        if reps > 0:
            studied.add(char)
        elif queue != _SUSPENDED_QUEUE:
            unlocked.add(char)
    return studied, unlocked


def read_anki_connect() -> tuple[set[str], set[str]]:
    from .activation import AnkiConnectClient

    client = AnkiConnectClient(api_key=os.getenv("ANKICONNECT_API_KEY", "").strip())
    studied = client.find_studied_characters()
    return studied, client.find_active_characters() - studied


def refresh_known(path: Path = KNOWN_PATH) -> KnownCharacters:
    from .activation import AnkiConnectError

    try:
        studied, unlocked = read_anki_connect()
        source = "ankiconnect"
    except (AnkiConnectError, OSError):
        studied, unlocked = read_collection()
        source = "collection file"
    known = KnownCharacters(
        studied=frozenset(studied),
        unlocked=frozenset(unlocked),
        source=source,
        updated=datetime.now().isoformat(timespec="seconds"),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": known.updated,
        "source": source,
        "studied": "".join(sorted(studied)),
        "unlocked": "".join(sorted(unlocked)),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return known


def load_known(path: Path = KNOWN_PATH) -> KnownCharacters:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["updated"][:10] == date.today().isoformat():
            return KnownCharacters(
                studied=frozenset(data["studied"]),
                unlocked=frozenset(data["unlocked"]),
                source=data["source"],
                updated=data["updated"],
            )
    return refresh_known(path)


def voice_lines(lines: list[str], *, voice_id: str = TUTOR_VOICE_ID) -> list[Path]:
    from .audio import build_tts_provider

    # One folder per voice, so switching voice never replays another voice's clip.
    out_dir = TUTOR_AUDIO_DIR / voice_id
    out_dir.mkdir(parents=True, exist_ok=True)
    provider = build_tts_provider(
        generated_audio_dir=out_dir, provider_name="minimax", mandarin_voice_id=voice_id
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        tags = list(pool.map(provider.generate_plain_mandarin, lines))
    return [out_dir / tag.removeprefix("[sound:").removesuffix("]") for tag in tags]


def play_in_background(paths: Iterable[Path]) -> bool:
    player = shutil.which("ffplay")
    if player is None:
        return False
    script = (
        "import subprocess,sys\n"
        "for clip in sys.argv[2:]:\n"
        "    subprocess.run([sys.argv[1],'-nodisp','-autoexit','-loglevel','quiet',clip])\n"
    )
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [sys.executable, "-c", script, player, *map(str, paths)],
        creationflags=flags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    return True


def log_new(new_chars: dict[str, str], path: Path = LOG_PATH) -> None:
    if not new_chars:
        return
    today = date.today().isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as log:
        for char, sentence in new_chars.items():
            entry = {"date": today, "char": char, "sentence": sentence}
            log.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recent_new(days: int = 7, path: Path = LOG_PATH) -> list[str]:
    if not path.exists():
        return []
    cutoff = date.fromordinal(date.today().toordinal() - days).isoformat()
    chars: dict[str, None] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry["date"] >= cutoff:
            chars[entry["char"]] = None
    return list(chars)
