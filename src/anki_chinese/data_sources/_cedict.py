"""
CC-CEDICT data source.

CC-CEDICT is a free, community-maintained Chinese-English dictionary with
~124,000 entries covering common and rare/classical characters.
License: Creative Commons Attribution-ShareAlike 4.0 International

Download URL (ZIP):
    https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip

The .zip contains a single .txt file with one entry per non-comment line:
    Traditional Simplified [pīn yīn] /meaning 1/meaning 2/.../

When the local file is absent this module automatically downloads and caches it at
data/reference/cedict_1_0_ts_utf-8_mdbg.txt.

Selection strategy per character:
    1. Prefer exact 2-character words (most useful as flashcard examples)
    2. Among same-length candidates, prefer highest SUBTLEX-CH frequency
    3. Fall back to shortest word length as a proxy for commonness
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from pypinyin.contrib.tone_convert import to_tone

_CEDICT_ZIP_URL = (
    "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip"
)

# Matches: Traditional Simplified [pinyin] /def1/def2/.../
_LINE_RE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$")

# Module-level caches
_index: dict[str, list[tuple[str, str, str]]] | None = None
_char_defs: dict[str, list[str]] | None = None


def _is_cjk(word: str) -> bool:
    return all("\u4e00" <= ch <= "\u9fff" for ch in word)


def _normalize_pinyin(text: str) -> str:
    return " ".join(text.lower().split())


def _cedict_pinyin_to_diacritical(text: str) -> str:
    return _normalize_pinyin(to_tone(text.replace("u:", "v").lower()))


def _looks_like_proper_noun_pinyin(text: str) -> bool:
    return text != text.lower()


def _download_and_cache(path: Path) -> str:
    """Download CC-CEDICT zip, extract the .txt, and cache it at *path*."""
    try:
        with urlopen(_CEDICT_ZIP_URL, timeout=60) as resp:
            raw = resp.read()
    except (TimeoutError, URLError, OSError) as exc:
        raise RuntimeError(f"Could not download CC-CEDICT: {exc}") from exc

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        # The archive ships as cedict_ts.u8 (UTF-8 text despite the extension)
        txt_names = [n for n in zf.namelist() if n.endswith((".txt", ".u8"))]
        if not txt_names:
            raise RuntimeError(
                f"No data file found inside CC-CEDICT zip: {zf.namelist()}"
            )
        content = zf.read(txt_names[0]).decode("utf-8")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return content


def _load_raw(path: Path) -> str:
    """Return CC-CEDICT text, downloading once if absent."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return _download_and_cache(path)


def build_index(
    path: Path,
    subtlex_path: Path | None = None,
) -> dict[str, list[tuple[str, str, str]]]:
    """Build {hanzi -> [(word, meaning, pinyin), ...]} from CC-CEDICT at *path*.

    Optionally scores candidates using SUBTLEX-CH frequency data when
    *subtlex_path* points to the SUBTLEX_CH.xlsx file.
    """
    text = _load_raw(path)

    # Load SUBTLEX frequencies if available
    freq_table: dict[str, float] = {}
    if subtlex_path is not None:
        from . import _subtlex

        if _subtlex.is_available(subtlex_path):
            freq_table = _subtlex.get_freq_table(subtlex_path)

    candidates: dict[str, list[tuple[int, bool, float, int, str, str, str]]] = {}

    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue

        simplified = m.group(2)
        raw_pinyin = m.group(3)
        pinyin = _cedict_pinyin_to_diacritical(m.group(3))
        definitions = m.group(4).split("/")
        meaning = definitions[0].strip() if definitions else ""

        if not simplified or not _is_cjk(simplified):
            continue
        wlen = len(simplified)
        if wlen < 2:
            continue

        freq = freq_table.get(simplified, 0.0)
        tier = 0 if wlen == 2 else 1
        proper_noun = _looks_like_proper_noun_pinyin(raw_pinyin)

        for ch in set(simplified):
            candidates.setdefault(ch, []).append(
                (tier, proper_noun, -freq, wlen, simplified, meaning, pinyin)
            )

    index: dict[str, list[tuple[str, str, str]]] = {}
    for ch, rows in candidates.items():
        rows.sort(key=lambda item: (item[0], item[1], item[2], item[3], item[4]))
        deduped: list[tuple[str, str, str]] = []
        seen: set[str] = set()
        for _, _, _, _, word, meaning, pinyin in rows:
            if word in seen:
                continue
            deduped.append((word, meaning, pinyin))
            seen.add(word)
        index[ch] = deduped

    return index


def lookup(
    hanzi: str,
    path: Path,
    subtlex_path: Path | None = None,
) -> list[tuple[str, str, str]]:
    """Return [(word, meaning, pinyin), ...] for *hanzi* from CC-CEDICT."""
    global _index
    if _index is None:
        _index = build_index(path, subtlex_path)
    return _index.get(hanzi, [])


def _build_char_defs(path: Path) -> dict[str, dict[str, list[str]]]:
    """Build {char: {pinyin: [def1, ...], ...}} for single-character CEDICT entries."""
    text = _load_raw(path)
    index: dict[str, dict[str, list[str]]] = {}
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        simp = m.group(2)
        if len(simp) != 1:
            continue
        raw_pinyin = m.group(3).strip()
        pinyin_key = _cedict_pinyin_to_diacritical(raw_pinyin)
        defs = [d.strip() for d in m.group(4).split("/") if d.strip()]
        clean = [
            d for d in defs
            if not d.startswith("surname ")
            and not d.startswith("variant of ")
            and not d.startswith("old variant of ")
            and not d.startswith("see ")
        ]
        if clean:
            index.setdefault(simp, {}).setdefault(pinyin_key, []).extend(clean)
    return index


def lookup_char_defs(hanzi: str, path: Path, *, pinyin: str = "") -> list[str]:
    """Return dictionary definitions for a single character from CC-CEDICT.

    When *pinyin* is provided (e.g. "tiáo"), returns only definitions for
    that pronunciation. Falls back to all definitions if no match.
    """
    global _char_defs
    if _char_defs is None:
        _char_defs = _build_char_defs(path)
    readings = _char_defs.get(hanzi, {})
    if not readings:
        return []
    if pinyin:
        normalized = _normalize_pinyin(pinyin)
        if normalized in readings:
            return readings[normalized]
    # Fall back to all definitions across all readings
    all_defs: list[str] = []
    for defs in readings.values():
        all_defs.extend(defs)
    return all_defs
