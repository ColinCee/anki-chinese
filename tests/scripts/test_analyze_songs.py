"""Tests for scripts/analyze_songs.py — pure logic functions only."""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

# Import the script as a module (PEP 723 block is just comments).
# Deps (opencc, requests, rich) are available via uv sync --group dev.
_script = Path(__file__).resolve().parent.parent.parent / "scripts" / "analyze_songs.py"
_spec = importlib.util.spec_from_file_location("analyze_songs", _script)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["analyze_songs"] = _mod
_spec.loader.exec_module(_mod)

is_cjk = _mod.is_cjk
extract_cjk = _mod.extract_cjk
parse_lyric_file = _mod.parse_lyric_file


# ── is_cjk ──


class TestIsCjk:
    def test_common_hanzi(self) -> None:
        assert is_cjk("中")
        assert is_cjk("猫")

    def test_cjk_extension_a(self) -> None:
        assert is_cjk("\u3400")
        assert is_cjk("\u4DBF")

    def test_boundary_just_outside(self) -> None:
        assert not is_cjk("\u4DFF")
        assert not is_cjk("\u33FF")

    def test_ascii(self) -> None:
        assert not is_cjk("a")
        assert not is_cjk("1")
        assert not is_cjk(" ")

    def test_punctuation_and_kana(self) -> None:
        assert not is_cjk("，")
        assert not is_cjk("の")
        assert not is_cjk("！")


# ── extract_cjk ──


class TestExtractCjk:
    def test_mixed_content(self) -> None:
        text = "Hello 你好 world 世界！123"
        assert extract_cjk(text) == {"你", "好", "世", "界"}

    def test_empty_string(self) -> None:
        assert extract_cjk("") == set()

    def test_no_cjk(self) -> None:
        assert extract_cjk("Hello world! 123") == set()

    def test_duplicates_collapsed(self) -> None:
        assert extract_cjk("猫猫猫") == {"猫"}

    def test_newlines_and_whitespace(self) -> None:
        assert extract_cjk("一\n二\n三\n") == {"一", "二", "三"}


# ── parse_lyric_file ──


class TestParseLyricFile:
    def test_basic_parse(self, tmp_path: Path) -> None:
        md = tmp_path / "test-song.md"
        md.write_text(
            textwrap.dedent("""\
                ---
                title: 学猫叫
                artist: 小潘潘
                ---
                我们一起学猫叫
                一起喵喵喵喵喵
            """),
            encoding="utf-8",
        )
        result = parse_lyric_file(md)
        assert result["title"] == "学猫叫"
        assert result["artist"] == "小潘潘"
        assert result["file"] == "test-song"
        assert "我" in result["characters"]
        assert "喵" in result["characters"]

    def test_missing_frontmatter_raises(self, tmp_path: Path) -> None:
        md = tmp_path / "bad.md"
        md.write_text("no frontmatter here\n", encoding="utf-8")
        with pytest.raises(ValueError, match="No frontmatter"):
            parse_lyric_file(md)

    def test_characters_exclude_punctuation(self, tmp_path: Path) -> None:
        md = tmp_path / "punct.md"
        md.write_text(
            textwrap.dedent("""\
                ---
                title: test
                ---
                你好！世界？
            """),
            encoding="utf-8",
        )
        result = parse_lyric_file(md)
        assert result["characters"] == {"你", "好", "世", "界"}

    def test_colon_in_value(self, tmp_path: Path) -> None:
        md = tmp_path / "colon.md"
        md.write_text(
            textwrap.dedent("""\
                ---
                title: 不舍：斗罗大陆
                artist: 王晰
                ---
                歌词
            """),
            encoding="utf-8",
        )
        result = parse_lyric_file(md)
        assert result["title"] == "不舍：斗罗大陆"


# ── Credit line stripping regex ──

import re

_CREDIT_PATTERN = re.compile(r"^(词|曲|编曲|作词|作曲|制作人?|演唱)\s*[：:]")


class TestCreditLineStripping:
    """Test the credit-line regex used in fetch_lyrics cleanup."""

    @pytest.mark.parametrize(
        "line",
        [
            "词：方文山",
            "曲：周杰伦",
            "编曲：黄雨勋",
            "作词：林夕",
            "作曲：陈奕迅",
            "制作人：荒井十一",
            "制作：荒井十一",
            "演唱：邓紫棋",
            "词:方文山",
            "曲: 周杰伦",
        ],
    )
    def test_credit_lines_matched(self, line: str) -> None:
        assert _CREDIT_PATTERN.match(line.strip()), f"Should match: {line}"

    @pytest.mark.parametrize(
        "line",
        [
            "我们一起学猫叫",
            "词语很美丽",
            "曲折的道路",
            "",
            "   ",
        ],
    )
    def test_lyrics_not_matched(self, line: str) -> None:
        assert not _CREDIT_PATTERN.match(line.strip()), f"Should NOT match: {line}"


# ── Greedy algorithm ──


class TestGreedySequence:
    """Test the greedy fewest-new-chars-first algorithm."""

    @staticmethod
    def _run_greedy(
        songs: list[dict], known: set[str], deck_chars: set[str]
    ) -> list[dict]:
        remaining = list(songs)
        sequence: list[dict] = []
        cumulative = set(known)
        while remaining:
            remaining.sort(
                key=lambda s: len((s["characters"] - cumulative) & deck_chars)
            )
            best = remaining.pop(0)
            sequence.append(best)
            cumulative |= (best["characters"] - cumulative) & deck_chars
        return sequence

    def test_picks_fewest_new_first(self) -> None:
        known = {"一", "二", "三"}
        deck = {"一", "二", "三", "四", "五", "六", "七", "八", "九", "十"}
        songs = [
            {"file": "hard", "characters": {"七", "八", "九", "十"}},
            {"file": "easy", "characters": {"一", "二", "四"}},
            {"file": "medium", "characters": {"一", "五", "六"}},
        ]
        seq = self._run_greedy(songs, known, deck)
        assert [s["file"] for s in seq] == ["easy", "medium", "hard"]

    def test_overlap_reduces_later_songs(self) -> None:
        known = {"一"}
        deck = {"一", "二", "三", "四", "五"}
        songs = [
            {"file": "a", "characters": {"一", "二", "三"}},
            {"file": "b", "characters": {"二", "三", "四"}},
        ]
        seq = self._run_greedy(songs, known, deck)
        # a has 2 new, b has 3 new → a first; then b only has 1 new (四)
        assert seq[0]["file"] == "a"
        assert seq[1]["file"] == "b"

    def test_empty_songs(self) -> None:
        assert self._run_greedy([], set(), set()) == []

    def test_all_known(self) -> None:
        known = {"一", "二"}
        deck = {"一", "二"}
        songs = [
            {"file": "a", "characters": {"一"}},
            {"file": "b", "characters": {"二"}},
        ]
        seq = self._run_greedy(songs, known, deck)
        assert len(seq) == 2

    def test_chars_not_in_deck_ignored(self) -> None:
        known: set[str] = set()
        deck = {"一", "二"}
        songs = [
            {"file": "a", "characters": {"一", "喵"}},
            {"file": "b", "characters": {"二"}},
        ]
        seq = self._run_greedy(songs, known, deck)
        # Both have 1 new deck char — all returned regardless
        assert len(seq) == 2
