"""Song lyric analysis and character activation planning."""

from .analysis import (
    SongActivationPlan,
    SongAnalysis,
    SongProgressRow,
    analyze_song_corpus,
    find_song,
    plan_song_activation,
)
from .fetch import (
    FetchedLyrics,
    LyricsSearchResult,
    fetch_lyrics_by_id,
    save_lyrics,
    search_lyrics,
)
from .lyrics import (
    LyricSong,
    extract_cjk,
    extract_study_cjk,
    is_cjk,
    load_songs,
    normalize_lyric_text_for_study,
    parse_lyric_file,
)

__all__ = [
    "FetchedLyrics",
    "LyricSong",
    "LyricsSearchResult",
    "SongActivationPlan",
    "SongAnalysis",
    "SongProgressRow",
    "analyze_song_corpus",
    "extract_cjk",
    "extract_study_cjk",
    "fetch_lyrics_by_id",
    "find_song",
    "is_cjk",
    "load_songs",
    "normalize_lyric_text_for_study",
    "parse_lyric_file",
    "plan_song_activation",
    "save_lyrics",
    "search_lyrics",
]
