"""Lyric file parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_LEXICAL_ZHU_NEXT_CHARS = {"作", "名", "者", "录", "錄", "述", "称", "稱"}
_LEXICAL_ZHU_PREV_CHARS = {"原", "土", "名", "显", "顯", "卓", "昭", "编", "編", "合", "巨", "译", "譯"}


@dataclass(frozen=True)
class LyricSong:
    file: str
    title: str
    artist: str
    lyrics: str
    characters: set[str]
    path: Path

    @property
    def label(self) -> str:
        return f"{self.title} ({self.artist})" if self.artist else self.title

    @property
    def study_characters(self) -> set[str]:
        return extract_study_cjk(self.lyrics)


def is_cjk(char: str) -> bool:
    cp = ord(char)
    return (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF)


def extract_cjk(text: str) -> set[str]:
    return {char for char in text if is_cjk(char)}


def _should_normalize_particle_zhe(text: str, index: int) -> bool:
    prev = text[index - 1] if index > 0 else ""
    next_char = text[index + 1] if index + 1 < len(text) else ""
    if not is_cjk(prev):
        return False
    if prev in _LEXICAL_ZHU_PREV_CHARS:
        return False
    return next_char not in _LEXICAL_ZHU_NEXT_CHARS


def normalize_lyric_text_for_study(text: str) -> str:
    """Normalize only the safe traditional forms used in mainland song planning."""
    chars: list[str] = []
    for index, char in enumerate(text):
        if char == "著" and _should_normalize_particle_zhe(text, index):
            chars.append("着")
            continue
        chars.append(char)
    return "".join(chars)


def extract_study_cjk(text: str) -> set[str]:
    return extract_cjk(normalize_lyric_text_for_study(text))


def parse_lyric_file(path: Path) -> LyricSong:
    """Parse a markdown lyric file with simple YAML-style frontmatter."""
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"No frontmatter found in {path}")

    frontmatter, lyrics = match.groups()
    metadata: dict[str, str] = {}
    for line in frontmatter.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    clean_lyrics = lyrics.strip()
    title = metadata.get("title", path.stem)
    artist = metadata.get("artist", "")
    return LyricSong(
        file=path.stem,
        title=title,
        artist=artist,
        lyrics=clean_lyrics,
        characters=extract_cjk(clean_lyrics),
        path=path,
    )


def load_songs(lyrics_dir: Path) -> list[LyricSong]:
    return [parse_lyric_file(path) for path in sorted(lyrics_dir.glob("*.md"))]
