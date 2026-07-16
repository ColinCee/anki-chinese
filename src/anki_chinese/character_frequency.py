"""Cached Mandarin character-frequency data and study coverage analysis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FREQUENCY_SOURCE_URL = (
    "https://lingua.mtsu.edu/chinese-computing/statistics/char/list.php?Which=frequency"
)
FREQUENCY_SOURCE_NAME = "Jun Da Chinese Character Frequency List"
FREQUENCY_SCHEMA_VERSION = 1


class FrequencyDataError(RuntimeError):
    """Raised when frequency data cannot be fetched, parsed, or loaded."""


@dataclass(frozen=True)
class FrequencyEntry:
    character: str
    rank: int
    frequency: int
    cumulative_percent: float
    pinyin: str

    def to_dict(self) -> dict[str, object]:
        return {
            "character": self.character,
            "rank": self.rank,
            "frequency": self.frequency,
            "cumulative_percent": self.cumulative_percent,
            "pinyin": self.pinyin,
        }


@dataclass(frozen=True)
class FrequencySnapshot:
    source_name: str
    source_url: str
    source_last_updated: str
    retrieved_at: str
    corpus_characters: int
    entries: tuple[FrequencyEntry, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": FREQUENCY_SCHEMA_VERSION,
            "source": {
                "name": self.source_name,
                "url": self.source_url,
                "last_updated": self.source_last_updated,
                "retrieved_at": self.retrieved_at,
            },
            "corpus_characters": self.corpus_characters,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class FrequencyReport:
    snapshot: FrequencySnapshot
    studied_characters: tuple[str, ...]
    deck_character_count: int
    covered_entries: tuple[FrequencyEntry, ...]
    gap_entries: tuple[FrequencyEntry, ...]
    unranked_gap_count: int
    studied_unranked_count: int
    corpus_coverage_frequency: int
    deck_covered_count: int
    estimated_band: str
    top_rank_coverage: tuple[tuple[int, float], ...]

    @property
    def studied_count(self) -> int:
        return len(self.studied_characters)

    @property
    def corpus_coverage_percent(self) -> float:
        if not self.snapshot.corpus_characters:
            return 0.0
        return 100 * self.corpus_coverage_frequency / self.snapshot.corpus_characters

    @property
    def deck_coverage_percent(self) -> float:
        if not self.deck_character_count:
            return 0.0
        return 100 * self.deck_covered_count / self.deck_character_count

    def to_dict(self, *, cache_path: Path) -> dict[str, object]:
        return {
            "cache_path": str(cache_path),
            "source": self.snapshot.to_dict()["source"],
            "corpus_characters": self.snapshot.corpus_characters,
            "studied_characters": list(self.studied_characters),
            "studied_count": self.studied_count,
            "deck_character_count": self.deck_character_count,
            "deck_covered_count": self.deck_covered_count,
            "deck_coverage_percent": self.deck_coverage_percent,
            "corpus_coverage_frequency": self.corpus_coverage_frequency,
            "corpus_coverage_percent": self.corpus_coverage_percent,
            "estimated_band": self.estimated_band,
            "studied_unranked_count": self.studied_unranked_count,
            "unranked_gap_count": self.unranked_gap_count,
            "top_rank_coverage": {
                str(rank): percent for rank, percent in self.top_rank_coverage
            },
            "covered_characters": [entry.to_dict() for entry in self.covered_entries],
            "top_frequency_gaps": [entry.to_dict() for entry in self.gap_entries],
        }


_ROW_RE = re.compile(
    r"(?P<rank>\d+)\t(?P<character>[^\t])\t(?P<frequency>\d+)\t"
    r"(?P<cumulative>[0-9.]+)\t(?P<pinyin>[^\t<]*)\t"
)
_DATE_RE = re.compile(r"Data last updated.*?(?P<date>\d{4}-\d{2}-\d{2})", re.DOTALL)
_CORPUS_RE = re.compile(r"Total number of characters in the corpus:\s*([\d,]+)")


def _is_hanzi(character: str) -> bool:
    if len(character) != 1:
        return False
    codepoint = ord(character)
    return (0x3400 <= codepoint <= 0x4DBF) or (0x4E00 <= codepoint <= 0x9FFF)


def parse_frequency_page(
    payload: bytes,
    *,
    source_url: str = FREQUENCY_SOURCE_URL,
    retrieved_at: str | None = None,
) -> FrequencySnapshot:
    """Parse the Jun Da HTML page into a compact, JSON-serializable snapshot."""
    try:
        text = payload.decode("gb18030")
    except UnicodeDecodeError as error:
        raise FrequencyDataError("The frequency source was not valid GB18030 text.") from error

    pre_match = re.search(r"<pre>(?P<body>.*?)</pre>", text, re.DOTALL | re.IGNORECASE)
    if pre_match is None:
        raise FrequencyDataError("The frequency source did not contain a character list.")

    entries: list[FrequencyEntry] = []
    for match in _ROW_RE.finditer(pre_match.group("body")):
        character = unescape(match.group("character"))
        if not _is_hanzi(character):
            continue
        entries.append(
            FrequencyEntry(
                character=character,
                rank=int(match.group("rank")),
                frequency=int(match.group("frequency")),
                cumulative_percent=float(match.group("cumulative")),
                pinyin=unescape(match.group("pinyin")).strip(),
            )
        )

    if not entries:
        raise FrequencyDataError("The frequency source contained no Hanzi records.")

    corpus_match = _CORPUS_RE.search(text)
    if corpus_match is None:
        raise FrequencyDataError("The frequency source did not report corpus size.")

    date_match = _DATE_RE.search(text)
    source_last_updated = date_match.group("date") if date_match else "unknown"
    retrieved = retrieved_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return FrequencySnapshot(
        source_name=FREQUENCY_SOURCE_NAME,
        source_url=source_url,
        source_last_updated=source_last_updated,
        retrieved_at=retrieved,
        corpus_characters=int(corpus_match.group(1).replace(",", "")),
        entries=tuple(entries),
    )


def fetch_frequency_snapshot(
    *,
    url: str = FREQUENCY_SOURCE_URL,
    timeout_seconds: float = 30.0,
) -> FrequencySnapshot:
    """Fetch the frequency source once; callers decide where to cache it."""
    request = Request(url, headers={"User-Agent": "anki-chinese character-frequency"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise FrequencyDataError(f"Could not fetch the frequency source: {error}") from error
    return parse_frequency_page(payload, source_url=url)


def load_frequency_snapshot(path: Path) -> FrequencySnapshot:
    """Load and validate a cached frequency snapshot."""
    if not path.exists():
        raise FrequencyDataError(
            f"No cached frequency snapshot found at {path}. "
            "Run `uv run anki-chinese frequency refresh` first."
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FrequencyDataError(f"Could not read frequency snapshot {path}: {error}") from error

    try:
        source = raw["source"]
        entries = tuple(
            FrequencyEntry(
                character=str(item["character"]),
                rank=int(item["rank"]),
                frequency=int(item["frequency"]),
                cumulative_percent=float(item["cumulative_percent"]),
                pinyin=str(item.get("pinyin", "")),
            )
            for item in raw["entries"]
        )
        snapshot = FrequencySnapshot(
            source_name=str(source["name"]),
            source_url=str(source["url"]),
            source_last_updated=str(source["last_updated"]),
            retrieved_at=str(source["retrieved_at"]),
            corpus_characters=int(raw["corpus_characters"]),
            entries=entries,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise FrequencyDataError(f"Invalid frequency snapshot {path}: {error}") from error

    if not snapshot.entries or snapshot.corpus_characters <= 0:
        raise FrequencyDataError(f"Invalid frequency snapshot {path}: no usable records.")
    return snapshot


def save_frequency_snapshot(snapshot: FrequencySnapshot, path: Path) -> None:
    """Persist the explicit refresh result as local derived state."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise FrequencyDataError(f"Could not write frequency snapshot {path}: {error}") from error


def _estimated_band(known_count: int) -> str:
    if known_count >= 3000:
        return "HSK 6+ style"
    if known_count >= 2000:
        return "HSK 5-6 style"
    if known_count >= 1200:
        return "HSK 4-5 style"
    if known_count >= 700:
        return "HSK 3-4 style"
    if known_count >= 400:
        return "HSK 2-3 style"
    if known_count >= 150:
        return "HSK 1-2 style"
    return "below HSK 1 style"


def build_frequency_report(
    snapshot: FrequencySnapshot,
    *,
    studied_characters: set[str],
    deck_characters: set[str],
    limit: int = 20,
) -> FrequencyReport:
    """Compare reviewed characters with ranked corpus characters."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    entries_by_character = {entry.character: entry for entry in snapshot.entries}
    studied = {char for char in studied_characters if _is_hanzi(char)}
    deck = {char for char in deck_characters if _is_hanzi(char)}
    covered = tuple(
        sorted(
            (entries_by_character[char] for char in studied if char in entries_by_character),
            key=lambda entry: entry.rank,
        )
    )
    gaps = tuple(
        sorted(
            (
                entries_by_character[char]
                for char in deck - studied
                if char in entries_by_character
            ),
            key=lambda entry: entry.rank,
        )[:limit]
    )
    corpus_coverage_frequency = sum(entry.frequency for entry in covered)
    top_rank_coverage: list[tuple[int, float]] = []
    for rank_limit in (100, 500, 1000, 2000):
        top_entries = [entry for entry in snapshot.entries if entry.rank <= rank_limit]
        top_total = sum(entry.frequency for entry in top_entries)
        top_covered = sum(entry.frequency for entry in top_entries if entry.character in studied)
        top_rank_coverage.append(
            (rank_limit, 100 * top_covered / top_total if top_total else 0.0)
        )

    return FrequencyReport(
        snapshot=snapshot,
        studied_characters=tuple(sorted(studied)),
        deck_character_count=len(deck),
        covered_entries=covered,
        gap_entries=gaps,
        unranked_gap_count=len((deck - studied) - entries_by_character.keys()),
        studied_unranked_count=len(studied - entries_by_character.keys()),
        corpus_coverage_frequency=corpus_coverage_frequency,
        deck_covered_count=len(deck & studied),
        estimated_band=_estimated_band(len(covered)),
        top_rank_coverage=tuple(top_rank_coverage),
    )
