"""Cached Mandarin word-frequency-derived character coverage analysis."""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

FREQUENCY_SOURCE_URL = "https://github.com/rspeer/wordfreq"
FREQUENCY_SOURCE_NAME = "wordfreq Chinese large word list"
FREQUENCY_SCHEMA_VERSION = 2
FREQUENCY_WORD_LIMIT = 100_000


class FrequencyDataError(RuntimeError):
    """Raised when frequency data cannot be built or loaded."""


@dataclass(frozen=True)
class FrequencyEntry:
    character: str
    rank: int
    frequency: float
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
    corpus_characters: int | None
    entries: tuple[FrequencyEntry, ...]
    parameters: dict[str, object] = field(default_factory=dict)

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
            "parameters": self.parameters,
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
    corpus_coverage_frequency: float
    deck_covered_count: int
    estimated_band: str
    top_rank_coverage: tuple[tuple[int, float], ...]
    top_rank_deck_counts: tuple[tuple[int, int, int, int], ...] = ()

    @property
    def studied_count(self) -> int:
        return len(self.studied_characters)

    @property
    def corpus_coverage_percent(self) -> float:
        total_frequency = (
            self.snapshot.corpus_characters
            if self.snapshot.corpus_characters is not None
            else sum(entry.frequency for entry in self.snapshot.entries)
        )
        if not total_frequency:
            return 0.0
        return 100 * self.corpus_coverage_frequency / total_frequency

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
            "source_parameters": self.snapshot.parameters,
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
            "top_rank_deck_counts": {
                str(rank): {
                    "reviewed": reviewed,
                    "unreviewed": unreviewed,
                    "in_deck": in_deck,
                }
                for rank, reviewed, unreviewed, in_deck in self.top_rank_deck_counts
            },
            "covered_characters": [entry.to_dict() for entry in self.covered_entries],
            "top_frequency_gaps": [entry.to_dict() for entry in self.gap_entries],
        }


def _is_hanzi(character: str) -> bool:
    if len(character) != 1:
        return False
    codepoint = ord(character)
    return (0x3400 <= codepoint <= 0x4DBF) or (0x4E00 <= codepoint <= 0x9FFF)


def build_wordfreq_snapshot(
    *,
    word_limit: int = FREQUENCY_WORD_LIMIT,
    retrieved_at: str | None = None,
    words: Iterable[str] | None = None,
    frequency_lookup: Callable[[str], float] | None = None,
) -> FrequencySnapshot:
    """Build a compact character ranking from wordfreq's precomputed word list."""
    if word_limit < 1:
        raise ValueError("word_limit must be at least 1")

    if words is None or frequency_lookup is None:
        try:
            import jieba  # noqa: F401
            from wordfreq import iter_wordlist, word_frequency
        except ImportError as error:
            raise FrequencyDataError(
                "wordfreq and jieba are required to build the frequency snapshot."
            ) from error
        words = iter_wordlist("zh", wordlist="large")

        def lookup_wordfreq(word: str) -> float:
            return word_frequency(word, "zh", wordlist="large")

        frequency_lookup = lookup_wordfreq

    assert words is not None
    assert frequency_lookup is not None
    scores: dict[str, float] = {}
    words_seen = 0
    hanzi_words_used = 0
    for word in words:
        if words_seen >= word_limit:
            break
        words_seen += 1
        if not word or not all(_is_hanzi(char) for char in word):
            continue
        frequency = frequency_lookup(word)
        if frequency <= 0:
            continue
        hanzi_words_used += 1
        for char in word:
            scores[char] = scores.get(char, 0.0) + frequency

    if not scores:
        raise FrequencyDataError("wordfreq produced no usable Hanzi frequency records.")

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    total_frequency = sum(frequency for _, frequency in ranked)
    cumulative_frequency = 0.0
    entries: list[FrequencyEntry] = []
    for rank, (character, frequency) in enumerate(ranked, start=1):
        cumulative_frequency += frequency
        entries.append(
            FrequencyEntry(
                character=character,
                rank=rank,
                frequency=frequency,
                cumulative_percent=100 * cumulative_frequency / total_frequency,
                pinyin="",
            )
        )

    retrieved = retrieved_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return FrequencySnapshot(
        source_name=FREQUENCY_SOURCE_NAME,
        source_url=FREQUENCY_SOURCE_URL,
        source_last_updated="approximately 2021",
        retrieved_at=retrieved,
        corpus_characters=None,
        entries=tuple(entries),
        parameters={
            "word_list": "large",
            "word_limit": word_limit,
            "words_seen": words_seen,
            "hanzi_words_used": hanzi_words_used,
            "character_score": "sum word frequency for each Hanzi occurrence",
        },
    )


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
        if raw["schema_version"] != FREQUENCY_SCHEMA_VERSION:
            raise FrequencyDataError(
                f"Frequency snapshot {path} uses an older schema. "
                "Run `uv run anki-chinese frequency refresh`."
            )
        source = raw["source"]
        entries = tuple(
            FrequencyEntry(
                character=str(item["character"]),
                rank=int(item["rank"]),
                frequency=float(item["frequency"]),
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
            corpus_characters=(
                int(raw["corpus_characters"])
                if raw.get("corpus_characters") is not None
                else None
            ),
            entries=entries,
            parameters=dict(raw.get("parameters", {})),
        )
    except FrequencyDataError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise FrequencyDataError(f"Invalid frequency snapshot {path}: {error}") from error

    if not snapshot.entries or (
        snapshot.corpus_characters is not None and snapshot.corpus_characters <= 0
    ):
        raise FrequencyDataError(f"Invalid frequency snapshot {path}: no usable records.")
    if any(
        entry.rank < 1
        or not _is_hanzi(entry.character)
        or not math.isfinite(entry.frequency)
        or entry.frequency <= 0
        or not math.isfinite(entry.cumulative_percent)
        or not 0 <= entry.cumulative_percent <= 100
        for entry in snapshot.entries
    ):
        raise FrequencyDataError(f"Invalid frequency snapshot {path}: invalid entry values.")
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
    top_rank_deck_counts: list[tuple[int, int, int, int]] = []
    for rank_limit in (100, 500, 1000, 2000):
        top_entries = [entry for entry in snapshot.entries if entry.rank <= rank_limit]
        top_characters = {entry.character for entry in top_entries}
        top_deck_characters = top_characters & deck
        top_reviewed_characters = top_deck_characters & studied
        top_total = sum(entry.frequency for entry in top_entries)
        top_covered = sum(
            entry.frequency for entry in top_entries if entry.character in top_reviewed_characters
        )
        top_rank_coverage.append(
            (rank_limit, 100 * top_covered / top_total if top_total else 0.0)
        )
        top_rank_deck_counts.append(
            (
                rank_limit,
                len(top_reviewed_characters),
                len(top_deck_characters - studied),
                len(top_deck_characters),
            )
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
        top_rank_deck_counts=tuple(top_rank_deck_counts),
    )
