"""Tests for songs verify command."""

from __future__ import annotations

import textwrap
from pathlib import Path

from anki_chinese.cli.songs import run_songs_verify


def _write_valid_song(lyrics_dir: Path, num: int, artist: str, title: str, body: str) -> None:
    lyrics_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{num:02d}-{artist}-{title}.md"
    content = f"---\ntitle: {title}\nartist: {artist}\n---\n{body}\n"
    (lyrics_dir / fname).write_text(content, encoding="utf-8")


_VALID_LYRICS = (
    "简单点说话的方式简单点\n"
    "递进的情节总有那么点冷清\n"
    "可你演技太过逼真一时让人分不清\n"
    "该配合你演出的我尽力在表演\n"
    "像情景剧一般可预料的画面\n"
)


def test_verify_passes_for_valid_corpus(runtime_factory) -> None:
    runtime = runtime_factory()
    lyrics_dir = runtime.song_lyrics_dir
    _write_valid_song(lyrics_dir, 1, "薛之谦", "演员", _VALID_LYRICS)
    _write_valid_song(lyrics_dir, 2, "林俊杰", "可惜没如果", _VALID_LYRICS)

    result = run_songs_verify(runtime, lyrics_dir=lyrics_dir)
    assert result is True
    assert "✓" in runtime.console.file.getvalue()


def test_verify_detects_traditional_characters(runtime_factory) -> None:
    runtime = runtime_factory()
    lyrics_dir = runtime.song_lyrics_dir
    _write_valid_song(lyrics_dir, 1, "歌手", "歌曲", "我們一起走過的日子\n那些年的記憶永遠不會消失\n")

    result = run_songs_verify(runtime, lyrics_dir=lyrics_dir)
    assert result is False
    output = runtime.console.file.getvalue()
    assert "Traditional characters" in output


def test_verify_detects_duplicate_titles(runtime_factory) -> None:
    runtime = runtime_factory()
    lyrics_dir = runtime.song_lyrics_dir
    _write_valid_song(lyrics_dir, 1, "歌手甲", "天后", "终于找到借口趁着醉意上心头\n表达我所有感受\n")
    _write_valid_song(lyrics_dir, 2, "歌手乙", "天后", "终于找到借口趁着醉意上心头\n表达我所有感受\n")

    result = run_songs_verify(runtime, lyrics_dir=lyrics_dir)
    assert result is False
    assert "Duplicate title" in runtime.console.file.getvalue()


def test_verify_detects_html_tags(runtime_factory) -> None:
    runtime = runtime_factory()
    lyrics_dir = runtime.song_lyrics_dir
    _write_valid_song(lyrics_dir, 1, "歌手", "歌曲", "<div>第一行歌词</div>\n第二行歌词\n")

    result = run_songs_verify(runtime, lyrics_dir=lyrics_dir)
    assert result is False
    assert "HTML tags" in runtime.console.file.getvalue()


def test_verify_detects_lrc_timestamps(runtime_factory) -> None:
    runtime = runtime_factory()
    lyrics_dir = runtime.song_lyrics_dir
    _write_valid_song(lyrics_dir, 1, "歌手", "歌曲", "[00:15.30]第一行歌词\n[00:20.00]第二行\n")

    result = run_songs_verify(runtime, lyrics_dir=lyrics_dir)
    assert result is False
    assert "LRC timestamps" in runtime.console.file.getvalue()


def test_verify_detects_numbering_gaps(runtime_factory) -> None:
    runtime = runtime_factory()
    lyrics_dir = runtime.song_lyrics_dir
    lyrics_dir.mkdir(parents=True, exist_ok=True)
    # Write file numbered 03 but it's the only file (should be 01)
    content = "---\ntitle: 歌曲\nartist: 歌手\n---\n简单点说话的方式简单点递进的情节\n"
    (lyrics_dir / "03-歌手-歌曲.md").write_text(content, encoding="utf-8")

    result = run_songs_verify(runtime, lyrics_dir=lyrics_dir)
    assert result is False
    assert "expected 01" in runtime.console.file.getvalue()


def test_verify_detects_missing_frontmatter_fields(runtime_factory) -> None:
    runtime = runtime_factory()
    lyrics_dir = runtime.song_lyrics_dir
    lyrics_dir.mkdir(parents=True, exist_ok=True)
    content = "---\ntitle: 歌曲\n---\n简单点说话的方式简单点递进的情节\n"
    (lyrics_dir / "01-歌手-歌曲.md").write_text(content, encoding="utf-8")

    result = run_songs_verify(runtime, lyrics_dir=lyrics_dir)
    assert result is False
    assert "Missing artist" in runtime.console.file.getvalue()
