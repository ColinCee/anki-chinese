"""Lyric file parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


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


def is_cjk(char: str) -> bool:
    cp = ord(char)
    return (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF)


def extract_cjk(text: str) -> set[str]:
    return {char for char in text if is_cjk(char)}


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
