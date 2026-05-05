"""Fetch song lyrics from lyrics.net.cn."""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

_LYRICS_BASE = "https://lyrics.net.cn"
_SEARCH_URL = f"{_LYRICS_BASE}/search/"
_LYRICS_URL = f"{_LYRICS_BASE}/lyrics/"

_SEARCH_RESULT_RE = re.compile(r'<a href="/lyrics/(\d+)">(.+?)</a>')
_LYRICS_MAIN_RE = re.compile(r'<div class="lyrics_main">(.*?)\n</div>', re.DOTALL)
_LYRICS_LINE_RE = re.compile(r"<div>(.*?)</div>")
_TITLE_RE = re.compile(r"<h2>(.*?)</h2>")
_ARTIST_RE = re.compile(r'<a id="artist"[^>]*>(.*?)</a>')


@dataclass(frozen=True)
class LyricsSearchResult:
    id: int
    title: str
    artist: str

    @property
    def url(self) -> str:
        return f"{_LYRICS_URL}{self.id}"

    @property
    def label(self) -> str:
        return f"{self.title} - {self.artist}" if self.artist else self.title


@dataclass(frozen=True)
class FetchedLyrics:
    title: str
    artist: str
    lyrics: str
    source_id: int


def _fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "anki-chinese/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def search_lyrics(query: str) -> list[LyricsSearchResult]:
    """Search lyrics.net.cn and return matching results."""
    params = urllib.parse.urlencode({"q": query})
    html = _fetch_html(f"{_SEARCH_URL}?{params}")

    results: list[LyricsSearchResult] = []
    seen_ids: set[int] = set()
    for match in _SEARCH_RESULT_RE.finditer(html):
        lyric_id = int(match.group(1))
        if lyric_id in seen_ids:
            continue
        seen_ids.add(lyric_id)
        label = match.group(2)
        # Format is "title-artist" in the link text
        if "-" in label:
            title, artist = label.rsplit("-", 1)
        else:
            title, artist = label, ""
        results.append(LyricsSearchResult(id=lyric_id, title=title.strip(), artist=artist.strip()))
    return results


def fetch_lyrics_by_id(lyric_id: int) -> FetchedLyrics:
    """Fetch lyrics from a lyrics.net.cn page by ID."""
    html = _fetch_html(f"{_LYRICS_URL}{lyric_id}")

    title_match = _TITLE_RE.search(html)
    title = title_match.group(1).strip() if title_match else ""

    artist_match = _ARTIST_RE.search(html)
    artist = artist_match.group(1).strip() if artist_match else ""

    lyrics_match = _LYRICS_MAIN_RE.search(html)
    if not lyrics_match:
        raise ValueError(f"No lyrics found on page {_LYRICS_URL}{lyric_id}")

    lyrics_html = lyrics_match.group(1)
    lines = [line.strip() for line in _LYRICS_LINE_RE.findall(lyrics_html)]
    # Strip credit lines (词：, 曲：, etc.)
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^(词|曲|编曲|作词|作曲|制作人?|演唱)\s*[：:]", stripped):
            continue
        cleaned.append(stripped)

    # Trim leading/trailing empty lines
    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()

    lyrics_text = "\n".join(cleaned)
    return FetchedLyrics(title=title, artist=artist, lyrics=lyrics_text, source_id=lyric_id)


def _sanitize_filename_part(name: str) -> str:
    """Remove characters that could cause path traversal or invalid filenames."""
    # Strip path separators and null bytes
    cleaned = name.replace("/", "").replace("\\", "").replace("\x00", "")
    # Collapse any ".." sequences
    cleaned = cleaned.replace("..", "")
    return cleaned.strip()


def _next_song_number(lyrics_dir: Path) -> int:
    """Return the next available song number based on existing files."""
    import re as _re

    max_num = 0
    if lyrics_dir.exists():
        for f in lyrics_dir.glob("*.md"):
            m = _re.match(r"^(\d+)-", f.name)
            if m:
                max_num = max(max_num, int(m.group(1)))
    return max_num + 1


def save_lyrics(
    fetched: FetchedLyrics,
    lyrics_dir: Path,
    *,
    artist_override: str = "",
    title_override: str = "",
) -> Path:
    """Save fetched lyrics as a numbered markdown file in the lyrics directory."""
    title = _sanitize_filename_part(title_override or fetched.title)
    artist = _sanitize_filename_part(artist_override or fetched.artist)

    num = _next_song_number(lyrics_dir)
    filename = f"{num:02d}-{artist}-{title}.md"
    filepath = (lyrics_dir / filename).resolve()
    # Guard against path traversal
    if not str(filepath).startswith(str(lyrics_dir.resolve())):
        raise ValueError(f"Unsafe filename would escape lyrics directory: {filename}")

    content = f"---\ntitle: {title}\nartist: {artist}\n---\n{fetched.lyrics}\n"
    lyrics_dir.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    return filepath
