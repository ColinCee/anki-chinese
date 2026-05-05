"""Tests for songs verify command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from anki_chinese.cli.songs import run_songs_verify, run_songs_verify_online
from anki_chinese.songs.fetch import FetchedLyrics, LyricsSearchResult


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
    # Use lyrics that contain the title characters
    _write_valid_song(
        lyrics_dir, 1, "薛之谦", "演员",
        "简单点说话的方式简单点\n该配合你演出的我尽力在表演员\n"
        "递进的情节总有那么点冷清\n可你演技太过逼真一时让人分不清\n"
        "像情景剧一般可预料的画面\n",
    )
    _write_valid_song(
        lyrics_dir, 2, "林俊杰", "可惜没如果",
        "假如把犯得起的错能错的都错过\n可惜没如果只剩下结果\n"
        "如果早点了解那率性的你\n没有想象中那么脆弱\n果然是这样\n",
    )

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


def test_verify_warns_on_title_chars_missing_from_lyrics(runtime_factory) -> None:
    runtime = runtime_factory()
    lyrics_dir = runtime.song_lyrics_dir
    # Title is "月亮代表我的心" but lyrics don't contain 代 or 表
    _write_valid_song(
        lyrics_dir, 1, "歌手", "月亮代表我的心",
        "你问我爱你有多深\n我爱你有几分\n轻轻的一个吻\n已经打动我的心\n月亮我的心\n",
    )

    result = run_songs_verify(runtime, lyrics_dir=lyrics_dir)
    # Warnings don't fail, but should be reported
    assert result is True
    output = runtime.console.file.getvalue()
    assert "Title chars missing from lyrics" in output
    assert "代" in output
    assert "表" in output


def test_verify_online_detects_missing_chars(runtime_factory) -> None:
    runtime = runtime_factory()
    lyrics_dir = runtime.song_lyrics_dir
    # Local lyrics missing 阳 光 彩 色 from the opening line
    _write_valid_song(
        lyrics_dir, 1, "邓紫棋", "泡沫",
        "就像被骗的我是幸福的\n追究什么对错你的谎言\n基于你还爱我\n美丽的泡沫\n虽然一刹花火\n",
    )

    mock_results = [LyricsSearchResult(id=652, title="泡沫", artist="G.E.M.邓紫棋")]
    mock_fetched = FetchedLyrics(
        title="泡沫",
        artist="G.E.M.邓紫棋",
        lyrics="阳光下的泡沫是彩色的\n就像被骗的我是幸福的\n追究什么对错你的谎言\n基于你还爱我\n美丽的泡沫\n虽然一刹花火\n", source_id=652,
    )

    with (
        patch("anki_chinese.cli.songs.search_lyrics", return_value=mock_results),
        patch("anki_chinese.cli.songs.fetch_lyrics_by_id", return_value=mock_fetched),
    ):
        result = run_songs_verify_online(runtime, lyrics_dir=lyrics_dir)

    assert result is False
    output = runtime.console.file.getvalue()
    assert "Missing" in output
    assert "阳" in output


def test_verify_online_passes_when_lyrics_match(runtime_factory) -> None:
    runtime = runtime_factory()
    lyrics_dir = runtime.song_lyrics_dir
    lyrics_text = "阳光下的泡沫是彩色的\n就像被骗的我是幸福的\n追究什么对错\n基于你还爱我\n美丽的泡沫\n"
    _write_valid_song(lyrics_dir, 1, "邓紫棋", "泡沫", lyrics_text)

    mock_results = [LyricsSearchResult(id=652, title="泡沫", artist="G.E.M.邓紫棋")]
    mock_fetched = FetchedLyrics(title="泡沫", artist="G.E.M.邓紫棋", lyrics=lyrics_text, source_id=652)

    with (
        patch("anki_chinese.cli.songs.search_lyrics", return_value=mock_results),
        patch("anki_chinese.cli.songs.fetch_lyrics_by_id", return_value=mock_fetched),
    ):
        result = run_songs_verify_online(runtime, lyrics_dir=lyrics_dir)

    assert result is True
    assert "✓" in runtime.console.file.getvalue()
