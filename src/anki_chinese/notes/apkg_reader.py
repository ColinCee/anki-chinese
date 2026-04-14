"""Parse Anki .apkg exports into `CharacterNote` objects."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

import io
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import zstandard as zstd

from ..config import MODEL_ID
from .model import CharacterNote

_FIELD_SEP = "\x1f"


def _decompress_anki21b(data: bytes) -> bytes:
    """Decompress a zstd-compressed .anki21b database."""
    reader = zstd.ZstdDecompressor().stream_reader(io.BytesIO(data))
    decompressed = reader.read()
    reader.close()
    return decompressed


def _extract_db(apkg_path: Path, tmp_dir: Path) -> Path:
    """Extract the SQLite database from an .apkg ZIP archive.

    Modern Anki exports contain a zstd-compressed ``collection.anki21b``.
    Older exports use an uncompressed ``collection.anki2``.  The
    ``collection.anki2`` that ships alongside ``.anki21b`` is a stub with a
    single "please upgrade" note, so the compressed variant always wins.
    """
    with zipfile.ZipFile(apkg_path, "r") as zf:
        names = zf.namelist()

        if "collection.anki21b" in names:
            compressed = zf.read("collection.anki21b")
            db_bytes = _decompress_anki21b(compressed)
            db_path = tmp_dir / "collection.sqlite"
            db_path.write_bytes(db_bytes)
            return db_path

        if "collection.anki2" in names:
            db_path = tmp_dir / "collection.anki2"
            db_path.write_bytes(zf.read("collection.anki2"))
            return db_path

        raise FileNotFoundError(
            f"No collection database found in {apkg_path}. "
            f"Contents: {names}"
        )


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def _extract_hanzi(raw: str) -> str:
    raw = raw.strip()
    if "<img" in raw:
        match = re.search(r'src="([0-9a-fA-F]+)\.gif"', raw)
        if match:
            return chr(int(match.group(1), 16))
    return _strip_html(raw)


def _note_from_fields(flds: str, tags: str) -> CharacterNote:
    """Build a CharacterNote from the \x1f-separated fields string."""
    parts = flds.split(_FIELD_SEP)

    def _get(idx: int) -> str:
        return parts[idx].strip() if idx < len(parts) else ""

    return CharacterNote(
        hanzi=_extract_hanzi(_get(0)),
        meaning=_strip_html(_get(1)),
        pinyin=_strip_html(_get(2)),
        jyutping=_strip_html(_get(3)),
        mandarin_audio=_get(4),
        cantonese_audio=_get(5),
        stroke_order=_get(6),
        heisig_num=_get(7),
        lesson=tags.strip() if tags.strip() else _get(8),
        story=_get(9),
        sentence_audio=_get(10),
        sentence=_get(11),
        sentence_pinyin=_get(12),
        sentence_english=_get(13),
    )


def parse_apkg(path: Path) -> list[CharacterNote]:
    """Parse an .apkg export into ``CharacterNote`` objects.

    Only notes matching the Chinese RSH model (``MODEL_ID``) are included.
    """
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _extract_db(path, Path(tmp))
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT flds, tags FROM notes WHERE mid = ? ORDER BY sfld",
                (MODEL_ID,),
            )
            notes = [_note_from_fields(flds, tags) for flds, tags in cur.fetchall()]
        finally:
            conn.close()

    return notes


def load_learned_hanzi_from_apkg(path: Path) -> set[str]:
    """Return the set of unsuspended (learned) hanzi from an .apkg export.

    A card with ``queue != -1`` is considered active (new, learning, or review).
    Since each note has two cards (recognition + listening), a character is
    "learned" if *any* of its cards are unsuspended.
    """
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _extract_db(path, Path(tmp))
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT substr(n.flds, 1, instr(n.flds, X'1F') - 1)
                FROM cards c
                JOIN notes n ON c.nid = n.id
                WHERE c.queue != -1
                  AND n.mid = ?
                """,
                (MODEL_ID,),
            )
            learned = {_extract_hanzi(row[0]) for row in cur.fetchall()}
        finally:
            conn.close()

    return learned
