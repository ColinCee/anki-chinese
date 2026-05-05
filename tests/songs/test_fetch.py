"""Tests for songs.fetch module."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from anki_chinese.songs.fetch import (
    FetchedLyrics,
    LyricsSearchResult,
    fetch_lyrics_by_id,
    save_lyrics,
    search_lyrics,
)

_SEARCH_HTML = textwrap.dedent("""\
    <html><body>
    <div class="search_title">按歌曲名搜索結果：</div>
    <div>
        <a href="/lyrics/12345">天后-陈势安</a>&nbsp;
        <a href="/lyrics/67890">天后-于冬然</a>&nbsp;
    </div>
    <div class="search_title">按歌词搜索結果：</div>
    <div>
        <a href="/lyrics/12345">天后-陈势安</a>&nbsp;
        <a href="/lyrics/99999">下一站天后-Twins</a>&nbsp;
    </div>
    </body></html>
""")

_LYRICS_HTML = textwrap.dedent("""\
    <html><body>
    <h2>天后</h2>
    <a id="artist" href="/artist/778" style="flex: 0 0 auto;">陈势安</a>
    <div class="lyrics_main">
        <div>终于找到借口趁着醉意上心头</div>
        <div>表达我所有感受</div>
        <div>寂寞渐浓 沉默留在舞池角落</div>
    </div>
    </div>
    </body></html>
""")


def test_search_lyrics_parses_results() -> None:
    with patch("anki_chinese.songs.fetch._fetch_html", return_value=_SEARCH_HTML):
        results = search_lyrics("天后")

    assert len(results) == 3
    assert results[0] == LyricsSearchResult(id=12345, title="天后", artist="陈势安")
    assert results[1] == LyricsSearchResult(id=67890, title="天后", artist="于冬然")
    assert results[2] == LyricsSearchResult(id=99999, title="下一站天后", artist="Twins")


def test_search_lyrics_deduplicates_ids() -> None:
    html = '<a href="/lyrics/100">歌-A</a> <a href="/lyrics/100">歌-A</a>'
    with patch("anki_chinese.songs.fetch._fetch_html", return_value=html):
        results = search_lyrics("歌")

    assert len(results) == 1


def test_fetch_lyrics_by_id_extracts_content() -> None:
    with patch("anki_chinese.songs.fetch._fetch_html", return_value=_LYRICS_HTML):
        fetched = fetch_lyrics_by_id(12345)

    assert fetched.title == "天后"
    assert fetched.artist == "陈势安"
    assert fetched.source_id == 12345
    assert "终于找到借口趁着醉意上心头" in fetched.lyrics
    assert "寂寞渐浓 沉默留在舞池角落" in fetched.lyrics
    assert "<div>" not in fetched.lyrics


def test_fetch_lyrics_by_id_strips_credits() -> None:
    html = textwrap.dedent("""\
        <html><body>
        <h2>测试</h2>
        <a id="artist" href="/artist/1">歌手</a>
        <div class="lyrics_main">
            <div>词：张三</div>
            <div>曲：李四</div>
            <div>编曲：王五</div>
            <div>第一行歌词</div>
            <div>第二行歌词</div>
        </div>
        </div>
        </body></html>
    """)
    with patch("anki_chinese.songs.fetch._fetch_html", return_value=html):
        fetched = fetch_lyrics_by_id(1)

    assert "词：张三" not in fetched.lyrics
    assert "曲：李四" not in fetched.lyrics
    assert "编曲：王五" not in fetched.lyrics
    assert "第一行歌词" in fetched.lyrics


def test_fetch_lyrics_by_id_raises_on_missing_lyrics() -> None:
    html = "<html><body><h2>Empty</h2></body></html>"
    with (
        patch("anki_chinese.songs.fetch._fetch_html", return_value=html),
        pytest.raises(ValueError, match="No lyrics found"),
    ):
        fetch_lyrics_by_id(999)


def test_save_lyrics_creates_markdown_file(tmp_path: Path) -> None:
    fetched = FetchedLyrics(
        title="天后", artist="陈势安", lyrics="终于找到借口\n表达我所有感受", source_id=58445
    )
    path = save_lyrics(fetched, tmp_path)

    assert path.name == "陈势安-天后.md"
    content = path.read_text(encoding="utf-8")
    assert "title: 天后" in content
    assert "artist: 陈势安" in content
    assert "终于找到借口" in content


def test_save_lyrics_with_overrides(tmp_path: Path) -> None:
    fetched = FetchedLyrics(
        title="天后", artist="陈势安", lyrics="歌词内容", source_id=1
    )
    path = save_lyrics(fetched, tmp_path, artist_override="于冬然", title_override="天后")

    assert path.name == "于冬然-天后.md"
    content = path.read_text(encoding="utf-8")
    assert "artist: 于冬然" in content


def test_lyrics_search_result_url() -> None:
    r = LyricsSearchResult(id=58445, title="天后", artist="陈势安")
    assert r.url == "https://lyrics.net.cn/lyrics/58445"
    assert r.label == "天后 - 陈势安"
