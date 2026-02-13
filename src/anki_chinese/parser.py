"""
Parse the old Anki text export into CharacterNote objects.

The old format is a tab-separated file with 16 columns.  We extract what we
can and leave the rest for the enrichment step.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import CharacterNote


def _strip_html(html: str) -> str:
    """Remove HTML tags, returning plain text."""
    return re.sub(r"<[^>]+>", "", html).strip()


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


def parse_old_deck(path: Path) -> list[CharacterNote]:
    """Parse the old All Decks.txt export file into CharacterNote objects.

    Columns (0-indexed, tab-separated):
        0  notetype      Chinese (basic)
        1  deck          Chinese
        2  character     一
        3  meaning       one
        4  stroke gif    <img src="4e00.gif">
        5  mnemonic      (usually empty)
        6  extra         (usually empty)
        7  pinyin html   <span class="tone1">yī</span>
        8  (empty)
        9  colored char  <span class="tone1">一</span>
       10  heisig num    1
       11  lesson        RSH1-L01
       12  mandarin snd  [sound:naver-xxxx.mp3]
       13  jyutping html (often empty)
       14  cantonese snd [sound:hypertts-xxxx.mp3]
       15  tags          (empty)
    """
    notes: list[CharacterNote] = []

    with open(path, encoding="utf-8") as f:
        # Skip header lines starting with #
        lines = [line for line in f if not line.startswith("#") and line.strip()]

    reader = csv.reader(lines, delimiter="\t")

    for row in reader:
        if len(row) < 15:
            continue

        # Extract the img tag as-is for stroke order
        stroke_html = row[4].strip()

        note = CharacterNote(
            hanzi=row[2].strip(),
            keyword=row[3].strip(),
            pinyin=_extract_pinyin(row[7]) if row[7].strip() else "",
            jyutping=_extract_jyutping(row[13]) if row[13].strip() else "",
            mandarin_audio=_extract_sound(row[12]) if row[12].strip() else "",
            cantonese_audio=_extract_sound(row[14]) if row[14].strip() else "",
            stroke_order=stroke_html,
            heisig_num=row[10].strip(),
            lesson=row[11].strip(),
            mnemonic=row[5].strip(),
        )
        notes.append(note)

    return notes
