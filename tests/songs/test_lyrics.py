from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from anki_chinese.songs import extract_cjk, is_cjk, parse_lyric_file


def test_is_cjk_detects_hanzi_and_extension_a() -> None:
    assert is_cjk("中")
    assert is_cjk("\u3400")
    assert not is_cjk("a")
    assert not is_cjk("，")


def test_extract_cjk_collapses_duplicates() -> None:
    assert extract_cjk("Hello 你好你好！") == {"你", "好"}


def test_parse_lyric_file_reads_frontmatter_and_characters(tmp_path: Path) -> None:
    path = tmp_path / "song.md"
    path.write_text(
        textwrap.dedent("""\
            ---
            title: 学猫叫
            artist: 小潘潘
            ---
            我们一起学猫叫
            一起喵喵喵
        """),
        encoding="utf-8",
    )

    song = parse_lyric_file(path)

    assert song.title == "学猫叫"
    assert song.artist == "小潘潘"
    assert song.file == "song"
    assert song.label == "学猫叫 (小潘潘)"
    assert "喵" in song.characters


def test_parse_lyric_file_missing_frontmatter_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.md"
    path.write_text("no frontmatter\n", encoding="utf-8")

    with pytest.raises(ValueError, match="No frontmatter"):
        parse_lyric_file(path)
