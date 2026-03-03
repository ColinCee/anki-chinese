"""
SUBTLEX-CH word frequency data source (optional).

SUBTLEX-CH is a subtitle-corpus frequency database covering ~46 million words
from Chinese film/TV subtitles (Cai & Brysbaert, 2010).  It provides real-world
usage frequency rather than curriculum-based HSK rankings.

Download:
    https://crr.ugent.be/subtlex-ch/SUBTLEX_CH_131_30.zip
    Save the extracted .xlsx file as:  data/SUBTLEX_CH.xlsx

If the file is absent this module returns an empty table silently — the
lookup chain simply falls back to word-length heuristics.

Key columns used:
    Word    — simplified Chinese word
    WF      — raw word frequency (higher = more common)
    WFpmw   — word frequency per million words (normalised, preferred)
"""

from __future__ import annotations

from pathlib import Path

# Module-level cache: word -> frequency (higher = more common)
_freq_table: dict[str, float] | None = None
_loaded_path: Path | None = None


def _load(path: Path) -> dict[str, float]:
    """Parse SUBTLEX-CH Excel file into {word: WFpmw}."""
    try:
        import openpyxl  # type: ignore[import-untyped]
    except ImportError:
        return {}

    if not path.exists():
        return {}

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return {}

    rows = iter(ws.iter_rows(values_only=True))

    # Find header row
    header: list[str] = []
    for row in rows:
        header = [str(c).strip() if c is not None else "" for c in row]
        if "Word" in header:
            break
    if not header:
        return {}

    try:
        word_col = header.index("Word")
        # Prefer WFpmw (normalised); fall back to WF (raw count)
        freq_col = header.index("WFpmw") if "WFpmw" in header else header.index("WF")
    except ValueError:
        return {}

    table: dict[str, float] = {}
    for row in rows:
        if row is None or len(row) <= max(word_col, freq_col):
            continue
        word = row[word_col]
        freq = row[freq_col]
        if not isinstance(word, str) or not word:
            continue
        try:
            table[word] = float(freq) if freq is not None else 0.0
        except (TypeError, ValueError):
            table[word] = 0.0

    wb.close()
    return table


def get_freq_table(path: Path) -> dict[str, float]:
    """Return the frequency table, loading from *path* on first call."""
    global _freq_table, _loaded_path
    if _freq_table is None or _loaded_path != path:
        _freq_table = _load(path)
        _loaded_path = path
    return _freq_table


def frequency(word: str, path: Path) -> float:
    """Return the WFpmw frequency for *word*, or 0.0 if unknown."""
    return get_freq_table(path).get(word, 0.0)


def is_available(path: Path) -> bool:
    """True when the SUBTLEX-CH file exists and openpyxl is importable."""
    if not path.exists():
        return False
    try:
        import openpyxl  # noqa: F401  # type: ignore[import-untyped]

        return True
    except ImportError:
        return False
