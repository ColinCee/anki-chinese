"""Song corpus analysis and activation planning."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .lyrics import LyricSong


@dataclass(frozen=True)
class SongProgressRow:
    song: LyricSong
    chars: int
    known: int
    known_percent: int
    new_deck_chars: tuple[str, ...]
    unique_chars: int
    non_deck_chars: tuple[str, ...]
    cumulative_deck_chars: int
    days: int


@dataclass(frozen=True)
class SongAnalysis:
    sequence: list[SongProgressRow]
    active_chars: set[str]
    learned_chars: set[str]
    deck_chars: set[str]
    song_chars: set[str]
    new_deck_chars: set[str]
    non_deck_chars: set[str]
    shared_chars: int
    average_songs_per_char: float
    total_days: int


@dataclass(frozen=True)
class SongActivationPlan:
    song: LyricSong
    chars: tuple[str, ...]
    already_active: tuple[str, ...]
    non_deck_chars: tuple[str, ...]
    remaining_after_limit: tuple[str, ...]


def _song_frequency(songs: list[LyricSong]) -> Counter[str]:
    freq: Counter[str] = Counter()
    for song in songs:
        for char in song.study_characters:
            freq[char] += 1
    return freq


def _sequence_songs(
    songs: list[LyricSong],
    *,
    learned_chars: set[str],
    deck_chars: set[str],
    requested_sequence: list[str] | None = None,
) -> list[LyricSong]:
    if requested_sequence:
        by_file = {song.file: song for song in songs}
        by_title = {song.title: song for song in songs}
        return [
            song
            for name in requested_sequence
            if (song := by_file.get(name) or by_title.get(name)) is not None
        ]

    remaining = list(songs)
    sequence: list[LyricSong] = []
    cumulative = set(learned_chars)
    while remaining:
        remaining.sort(key=lambda song: len((song.study_characters - cumulative) & deck_chars))
        best = remaining.pop(0)
        sequence.append(best)
        cumulative |= (best.study_characters - cumulative) & deck_chars
    return sequence


def analyze_song_corpus(
    songs: list[LyricSong],
    *,
    active_chars: set[str],
    deck_chars: set[str],
    learned_chars: set[str] | None = None,
    pace: int = 5,
    requested_sequence: list[str] | None = None,
) -> SongAnalysis:
    if pace < 1:
        raise ValueError("pace must be at least 1")

    known_chars = active_chars if learned_chars is None else learned_chars
    freq = _song_frequency(songs)
    sequence = _sequence_songs(
        songs,
        learned_chars=known_chars,
        deck_chars=deck_chars,
        requested_sequence=requested_sequence,
    )

    cumulative = set(known_chars)
    rows: list[SongProgressRow] = []
    total_days = 0
    for song in sequence:
        chars = song.study_characters
        new = (chars - cumulative) & deck_chars
        non_deck = chars - deck_chars
        known_count = len(chars & cumulative)
        known_percent = round(known_count / len(chars) * 100) if chars else 0
        cumulative |= new
        days = len(new) // pace + (1 if len(new) % pace else 0)
        total_days += days
        rows.append(
            SongProgressRow(
                song=song,
                chars=len(chars),
                known=known_count,
                known_percent=known_percent,
                new_deck_chars=tuple(sorted(new)),
                unique_chars=sum(1 for char in chars if freq[char] == 1),
                non_deck_chars=tuple(sorted(non_deck)),
                cumulative_deck_chars=len(cumulative),
                days=days,
            )
        )

    song_chars: set[str] = set()
    for song in songs:
        song_chars |= song.study_characters

    average_songs_per_char = sum(freq.values()) / len(freq) if freq else 0.0
    return SongAnalysis(
        sequence=rows,
        active_chars=active_chars,
        learned_chars=known_chars,
        deck_chars=deck_chars,
        song_chars=song_chars,
        new_deck_chars=(song_chars - known_chars) & deck_chars,
        non_deck_chars=song_chars - deck_chars,
        shared_chars=sum(1 for count in freq.values() if count >= 2),
        average_songs_per_char=average_songs_per_char,
        total_days=total_days,
    )


def find_song(songs: list[LyricSong], query: str) -> LyricSong | None:
    normalized = query.strip()
    for song in songs:
        if normalized in {song.file, song.title, song.label}:
            return song
    matches = [
        song
        for song in songs
        if normalized in song.file or normalized in song.title or normalized in song.label
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def plan_song_activation(
    song: LyricSong,
    *,
    active_chars: set[str],
    deck_chars: set[str],
    deck_order: list[str] | None = None,
    limit: int = 0,
) -> SongActivationPlan:
    study_chars = song.study_characters
    activatable_chars = (study_chars - active_chars) & deck_chars
    ordered = (
        [char for char in deck_order if char in activatable_chars]
        if deck_order is not None
        else sorted(activatable_chars)
    )
    ordered.extend(sorted(activatable_chars - set(ordered)))
    activatable = tuple(ordered)
    if limit > 0:
        selected = activatable[:limit]
        remaining = activatable[limit:]
    else:
        selected = activatable
        remaining = ()

    return SongActivationPlan(
        song=song,
        chars=selected,
        already_active=tuple(sorted(study_chars & active_chars)),
        non_deck_chars=tuple(sorted(study_chars - deck_chars)),
        remaining_after_limit=remaining,
    )
