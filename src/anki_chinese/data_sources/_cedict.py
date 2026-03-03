"""
CC-CEDICT data source.

CC-CEDICT is a free, community-maintained Chinese-English dictionary with
~124,000 entries covering common and rare/classical characters.
License: Creative Commons Attribution-ShareAlike 4.0 International

Download URL (ZIP):
    https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip

The .zip contains a single .txt file with one entry per non-comment line:
    Traditional Simplified [pīn yīn] /meaning 1/meaning 2/.../

On first use this module automatically downloads and caches the file at
data/cedict_1_0_ts_utf-8_mdbg.txt.

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

_CEDICT_ZIP_URL = (
    "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip"
)

# Matches: Traditional Simplified [pinyin] /def1/def2/.../
_LINE_RE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$")

# Module-level cache
_index: dict[str, tuple[str, str]] | None = None


def _is_cjk(word: str) -> bool:
    return all("\u4e00" <= ch <= "\u9fff" for ch in word)


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
            raise RuntimeError(f"No data file found inside CC-CEDICT zip: {zf.namelist()}")
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
) -> dict[str, tuple[str, str]]:
    """Build {hanzi -> (best_word, meaning)} from CC-CEDICT at *path*.

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

    # best[ch] = (word, meaning, freq, word_len)
    best: dict[str, tuple[str, str, float, int]] = {}

    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue

        simplified = m.group(2)
        definitions = m.group(4).split("/")
        meaning = definitions[0].strip() if definitions else ""

        if not simplified or not _is_cjk(simplified):
            continue
        wlen = len(simplified)
        if wlen < 2:
            continue

        freq = freq_table.get(simplified, 0.0)
        is_two_char = wlen == 2

        for ch in set(simplified):
            prev = best.get(ch)
            if prev is None:
                best[ch] = (simplified, meaning, freq, wlen)
                continue

            _, _, prev_freq, prev_len = prev
            prev_two = prev_len == 2

            # 2-char words beat longer words
            if is_two_char and not prev_two:
                best[ch] = (simplified, meaning, freq, wlen)
            elif is_two_char == prev_two:
                # Same tier — prefer higher SUBTLEX frequency
                if freq > prev_freq:
                    best[ch] = (simplified, meaning, freq, wlen)
                elif freq == prev_freq and wlen < prev_len:
                    # Last resort: shorter word
                    best[ch] = (simplified, meaning, freq, wlen)

    return {ch: (word, meaning) for ch, (word, meaning, _, _) in best.items()}


def lookup(hanzi: str, path: Path, subtlex_path: Path | None = None) -> tuple[str, str]:
    """Return (word, meaning) for *hanzi* from CC-CEDICT, or ("", "")."""
    global _index
    if _index is None:
        _index = build_index(path, subtlex_path)
    return _index.get(hanzi, ("", ""))
