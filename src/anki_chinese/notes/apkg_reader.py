"""Parse Anki .apkg exports into `CharacterNote` objects."""

from __future__ import annotations

__all__: list[str] = []  # Internal module — import from package instead

import io
import re
import sqlite3
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

import zstandard as zstd

from ..config import MODEL_ID
from .model import CharacterNote, Curriculum

_FIELD_SEP = "\x1f"
_FIELD_KEYS = (
    "hanzi",
    "meaning",
    "pinyin",
    "jyutping",
    "mandarin_audio",
    "cantonese_audio",
    "stroke_order",
    "heisig_num",
    "lesson",
    "story",
    "sentence_audio",
    "sentence",
    "sentence_pinyin",
    "sentence_english",
)
_FIELD_INDEX = {field_name: index for index, field_name in enumerate(_FIELD_KEYS)}
_RSH_LESSON_RE = re.compile(r"(RSH\d+-L\d+)(?![A-Za-z0-9])", re.IGNORECASE)
_RSH_LABEL_RE = re.compile(r"RSH\d+-[A-Za-z0-9_]+$", re.IGNORECASE)


def _decompress_anki21b(data: bytes) -> bytes:
    """Decompress a zstd-compressed .anki21b database."""
    reader = zstd.ZstdDecompressor().stream_reader(io.BytesIO(data))
    decompressed = reader.read()
    reader.close()
    return decompressed


def _compress_anki21b(data: bytes) -> bytes:
    return zstd.ZstdCompressor().compress(data)


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


def _split_fields(flds: str) -> list[str]:
    parts = flds.split(_FIELD_SEP)
    if len(parts) < len(_FIELD_KEYS):
        parts.extend([""] * (len(_FIELD_KEYS) - len(parts)))
    return parts


def _curriculum_from_apkg(
    *,
    heisig_num: str,
    lesson_field: str,
    tags: str,
) -> Curriculum:
    tokens = tags.split()
    values: dict[str, str] = {}
    for token in tokens:
        if "::" in token:
            key, value = token.split("::", 1)
            values[key] = value

    explicit_lesson = values.get("lesson", "").strip()
    legacy_lesson = lesson_field.strip()
    custom = (
        values.get("curriculum") == "custom"
        or values.get("origin") == "manual"
        or explicit_lesson.startswith("Manual-Missing-")
        or legacy_lesson.startswith("Manual-Missing-")
    )
    if custom:
        custom_collection = values.get("collection", "").strip()
        if not custom_collection:
            for candidate in (explicit_lesson, legacy_lesson):
                if candidate.startswith("Manual-Missing-"):
                    custom_collection = candidate
                    break
        custom_lesson = (
            explicit_lesson
            if explicit_lesson and not explicit_lesson.startswith("Manual-Missing-")
            else ""
        )
        return Curriculum(
            track="custom",
            rsh_number=None,
            lesson=custom_lesson,
            origin=values.get("origin", "manual"),
            collection=custom_collection,
        )

    lesson_candidates = [explicit_lesson, legacy_lesson, *tokens]
    lesson = ""
    for candidate in lesson_candidates:
        match = _RSH_LESSON_RE.search(candidate)
        if match:
            lesson = match.group(1)
            break
    if not lesson:
        for candidate in lesson_candidates:
            stripped = candidate.strip()
            if stripped.startswith("Manual-Missing-"):
                lesson = stripped
                break
            if _RSH_LABEL_RE.fullmatch(stripped):
                lesson = stripped
                break
    if not lesson:
        fallback = explicit_lesson or legacy_lesson
        if fallback and not fallback.lower().startswith("leech"):
            lesson = fallback
    raw_number = values.get("rsh") or "".join(character for character in heisig_num if character.isdigit())
    return Curriculum(
        track="rsh",
        rsh_number=int(raw_number) if raw_number else None,
        lesson=lesson,
        origin=values.get("origin", "rsh"),
        collection=values.get("collection", ""),
    )


def _note_from_fields(flds: str, tags: str) -> CharacterNote:
    """Build a CharacterNote from the \x1f-separated fields string."""
    parts = _split_fields(flds)

    def _get(idx: int) -> str:
        return parts[idx].strip() if idx < len(parts) else ""

    curriculum = _curriculum_from_apkg(
        heisig_num=_get(7),
        lesson_field=_get(8),
        tags=tags,
    )
    return CharacterNote(
        hanzi=_extract_hanzi(_get(0)),
        meaning=_strip_html(_get(1)),
        pinyin=_strip_html(_get(2)),
        jyutping=_strip_html(_get(3)),
        mandarin_audio=_get(4),
        cantonese_audio=_get(5),
        stroke_order=_get(6),
        heisig_num=_get(7),
        lesson=curriculum.lesson,
        story=_get(9),
        sentence_audio=_get(10),
        sentence=_get(11),
        sentence_pinyin=_get(12),
        sentence_english=_get(13),
        curriculum=curriculum,
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


def update_note_fields_in_apkg(
    apkg_path: Path,
    hanzi: str,
    updates: dict[str, Any],
) -> CharacterNote:
    """Update one model note inside a source .apkg and return the updated note."""

    if not apkg_path.exists():
        raise FileNotFoundError(apkg_path)

    unsupported = sorted(set(updates) - set(_FIELD_INDEX))
    if unsupported:
        raise ValueError(f"Unsupported APKG note fields: {', '.join(unsupported)}")

    with tempfile.TemporaryDirectory(dir=apkg_path.parent) as tmp:
        tmp_dir = Path(tmp)
        db_path = tmp_dir / "collection.sqlite"

        with zipfile.ZipFile(apkg_path, "r") as zf:
            names = zf.namelist()
            if "collection.anki21b" in names:
                collection_name = "collection.anki21b"
                db_path.write_bytes(_decompress_anki21b(zf.read(collection_name)))
                compress_db = True
            elif "collection.anki2" in names:
                collection_name = "collection.anki2"
                db_path.write_bytes(zf.read(collection_name))
                compress_db = False
            else:
                raise FileNotFoundError(
                    f"No collection database found in {apkg_path}. Contents: {names}"
                )

        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, flds, tags FROM notes WHERE mid = ?", (MODEL_ID,))
            matches: list[tuple[int, list[str], str]] = []
            for note_id, flds, tags in cur.fetchall():
                parts = _split_fields(flds)
                if _extract_hanzi(parts[0]) == hanzi:
                    matches.append((note_id, parts, tags))

            if not matches:
                raise KeyError(f"{hanzi} is not in {apkg_path}")
            if len(matches) > 1:
                raise ValueError(f"{hanzi} matched {len(matches)} notes in {apkg_path}")

            note_id, parts, tags = matches[0]
            for field_name, value in updates.items():
                parts[_FIELD_INDEX[field_name]] = str(value)

            updated_fields = _FIELD_SEP.join(parts)
            cur.execute(
                "UPDATE notes SET flds = ?, mod = ? WHERE id = ?",
                (updated_fields, int(time.time()), note_id),
            )
            conn.commit()
            updated_note = _note_from_fields(updated_fields, tags)
        finally:
            conn.close()

        db_bytes = db_path.read_bytes()
        if compress_db:
            db_bytes = _compress_anki21b(db_bytes)

        rewritten_apkg = tmp_dir / apkg_path.name
        with zipfile.ZipFile(apkg_path, "r") as src, zipfile.ZipFile(rewritten_apkg, "w") as dst:
            dst.comment = src.comment
            for info in src.infolist():
                data = db_bytes if info.filename == collection_name else src.read(info.filename)
                dst.writestr(info, data)

        rewritten_apkg.replace(apkg_path)

    return updated_note


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


def load_deck_hanzi_from_apkg(path: Path) -> set[str]:
    """Return every single-character hanzi in the configured Chinese model."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _extract_db(path, Path(tmp))
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT flds
                FROM notes
                WHERE mid = ?
                """,
                (MODEL_ID,),
            )
            deck_chars = {
                hanzi
                for (flds,) in cur.fetchall()
                if len(hanzi := _extract_hanzi(flds.split(_FIELD_SEP)[0])) == 1
            }
        finally:
            conn.close()

    return deck_chars
