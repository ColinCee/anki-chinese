"""Parse Anki text exports into CharacterNote objects.

Supports both:
1) Legacy `All Decks.txt` schema (16 columns, no GUID column).
2) Current `Exported-deck.txt` schema (17 columns, GUID column first).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import CharacterNote


def _strip_html(html: str) -> str:
    """Remove HTML tags, returning plain text."""
    return re.sub(r"<[^>]+>", "", html).strip()


def _extract_hanzi(raw: str) -> str:
    """Extract the hanzi character from column 2.

    Usually this is just the character itself, but some rows have an
    ``<img src="770b.gif" />`` tag instead.  The filename is the Unicode
    codepoint in hex, so we can recover the character from it.
    """
    raw = raw.strip()
    if "<img" in raw:
        match = re.search(r'src="([0-9a-fA-F]+)\.gif"', raw)
        if match:
            return chr(int(match.group(1), 16))
    return raw


def _extract_pinyin(html: str) -> str:
    """Extract plain pinyin from '<span class="tone1">yī</span> <!-- yi -->'."""
    # The actual pinyin with diacriticals is inside the span
    match = re.search(r'class="tone\d">(.*?)</span>', html)
    if match:
        return match.group(1)
    return _strip_html(html)


def _extract_jyutping(html: str) -> str:
    """Extract plain jyutping from '<span class="tone2">gau2</span> <!-- ... -->'."""
    match = re.search(r'class="tone\d">(.*?)</span>', html)
    if match:
        return match.group(1)
    return _strip_html(html)


def _extract_sound(text: str) -> str:
    """Extract '[sound:filename.mp3]' tag, if present."""
    match = re.search(r"\[sound:[^\]]+\]", text)
    return match.group(0) if match else ""


def _parse_header_map(path: Path) -> dict[str, int]:
    """Return header-declared column map as 0-based indexes.

    Example header line: '#guid column:1'
    """
    column_map: dict[str, int] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#"):
                continue
            match = re.match(r"#([\w-]+)\s+column:(\d+)", line.strip())
            if not match:
                continue
            key = match.group(1).strip().lower()
            column_map[key] = int(match.group(2)) - 1
    return column_map


def _parse_legacy_row(row: list[str]) -> CharacterNote:
    """Parse one row from legacy `All Decks.txt` layout."""
    return CharacterNote(
        hanzi=_extract_hanzi(row[2]),
        keyword=row[3].strip(),
        pinyin=_extract_pinyin(row[7]) if row[7].strip() else "",
        jyutping=_extract_jyutping(row[13]) if row[13].strip() else "",
        mandarin_audio=_extract_sound(row[12]) if row[12].strip() else "",
        cantonese_audio=_extract_sound(row[14]) if row[14].strip() else "",
        stroke_order=row[4].strip(),
        heisig_num=row[10].strip(),
        lesson=row[11].strip(),
        mnemonic=row[5].strip(),
    )


def _parse_exported_row(row: list[str]) -> CharacterNote:
    """Parse one row from current `Exported-deck.txt` layout."""
    return CharacterNote(
        hanzi=_extract_hanzi(row[3]),
        keyword=row[4].strip(),
        pinyin=_extract_pinyin(row[5]) if row[5].strip() else "",
        jyutping=_extract_jyutping(row[6]) if row[6].strip() else "",
        mandarin_audio=_extract_sound(row[7]) if row[7].strip() else "",
        cantonese_audio=_extract_sound(row[8]) if row[8].strip() else "",
        example_word=row[9].strip(),
        example_meaning=row[10].strip(),
        example_audio=_extract_sound(row[11]) if row[11].strip() else "",
        stroke_order=row[12].strip(),
        heisig_num=row[13].strip(),
        lesson=row[14].strip(),
        mnemonic=row[15].strip(),
    )


def parse_deck_export(path: Path) -> list[CharacterNote]:
    """Parse source export into CharacterNote objects.

    Auto-detects schema via export headers. Falls back to row-length heuristic
    if headers are missing.
    """
    notes: list[CharacterNote] = []
    header_map = _parse_header_map(path)
    is_exported = "guid" in header_map

    with open(path, encoding="utf-8") as f:
        # Skip header lines starting with #
        lines = [line for line in f if not line.startswith("#") and line.strip()]

    reader = csv.reader(lines, delimiter="\t")

    for row in reader:
        if len(row) < 16:
            continue

        if is_exported or len(row) >= 17:
            note = _parse_exported_row(row)
        else:
            note = _parse_legacy_row(row)
        notes.append(note)

    return notes


def parse_old_deck(path: Path) -> list[CharacterNote]:
    """Backward-compatible alias for older callers."""
    return parse_deck_export(path)
