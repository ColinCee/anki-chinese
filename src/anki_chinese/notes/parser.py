"""Parse Anki text exports into `CharacterNote` objects."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .model import CharacterNote


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def _extract_hanzi(raw: str) -> str:
    raw = raw.strip()
    if "<img" in raw:
        match = re.search(r'src="([0-9a-fA-F]+)\.gif"', raw)
        if match:
            return chr(int(match.group(1), 16))
    return raw


def _extract_pinyin(html: str) -> str:
    match = re.search(r'class="tone\d">(.*?)</span>', html)
    if match:
        return match.group(1)
    return _strip_html(html)


def _extract_jyutping(html: str) -> str:
    match = re.search(r'class="tone\d">(.*?)</span>', html)
    if match:
        return match.group(1)
    return _strip_html(html)


def _extract_sound(text: str) -> str:
    match = re.search(r"\[sound:[^\]]+\]", text)
    return match.group(0) if match else ""


def _parse_header_map(path: Path) -> dict[str, int]:
    column_map: dict[str, int] = {}
    with open(path, encoding="utf-8") as file:
        for line in file:
            if not line.startswith("#"):
                continue
            match = re.match(r"#([\w-]+)\s+column:(\d+)", line.strip())
            if not match:
                continue
            key = match.group(1).strip().lower()
            column_map[key] = int(match.group(2)) - 1
    return column_map


def _parse_legacy_row(row: list[str]) -> CharacterNote:
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
        story=row[5].strip(),
    )


def _parse_exported_row(row: list[str]) -> CharacterNote:
    return CharacterNote(
        hanzi=_extract_hanzi(row[3]),
        keyword=row[4].strip(),
        pinyin=_extract_pinyin(row[5]) if row[5].strip() else "",
        jyutping=_extract_jyutping(row[6]) if row[6].strip() else "",
        mandarin_audio=_extract_sound(row[7]) if row[7].strip() else "",
        cantonese_audio=_extract_sound(row[8]) if row[8].strip() else "",
        example_word=row[9].strip(),
        example_meaning=row[10].strip(),
        example_pinyin=row[11].strip(),
        example_audio=_extract_sound(row[12]) if row[12].strip() else "",
        stroke_order=row[13].strip(),
        heisig_num=row[14].strip(),
        lesson=row[15].strip(),
        story=row[16].strip() if len(row) > 16 else "",
    )


def parse_deck_export(path: Path) -> list[CharacterNote]:
    """Parse source export into `CharacterNote` objects."""
    notes: list[CharacterNote] = []
    header_map = _parse_header_map(path)
    is_exported = "guid" in header_map

    with open(path, encoding="utf-8") as file:
        lines = [line for line in file if not line.startswith("#") and line.strip()]

    reader = csv.reader(lines, delimiter="\t")
    for row in reader:
        if len(row) < 16:
            continue
        notes.append(_parse_exported_row(row) if is_exported or len(row) >= 17 else _parse_legacy_row(row))
    return notes


def parse_old_deck(path: Path) -> list[CharacterNote]:
    return parse_deck_export(path)
