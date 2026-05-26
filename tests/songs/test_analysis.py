from __future__ import annotations

from pathlib import Path

from anki_chinese.songs import LyricSong, analyze_song_corpus, find_song, plan_song_activation


def _song(file: str, title: str, chars: set[str]) -> LyricSong:
    return LyricSong(
        file=file,
        title=title,
        artist="",
        lyrics="".join(chars),
        characters=chars,
        path=Path(f"{file}.md"),
    )


def test_analyze_song_corpus_orders_by_fewest_new_deck_chars() -> None:
    songs = [
        _song("hard", "Hard", {"七", "八", "九"}),
        _song("easy", "Easy", {"一", "二"}),
        _song("medium", "Medium", {"一", "三", "四"}),
    ]

    analysis = analyze_song_corpus(
        songs,
        active_chars={"一"},
        deck_chars={"一", "二", "三", "四", "七", "八", "九"},
        pace=2,
    )

    assert [row.song.file for row in analysis.sequence] == ["easy", "medium", "hard"]
    assert analysis.total_days == 4
    assert analysis.new_deck_chars == {"二", "三", "四", "七", "八", "九"}


def test_analyze_song_corpus_counts_active_unstudied_as_new() -> None:
    songs = [_song("song", "Song", {"一", "二", "三"})]

    analysis = analyze_song_corpus(
        songs,
        active_chars={"一", "二", "三"},
        learned_chars={"一"},
        deck_chars={"一", "二", "三"},
        pace=2,
    )

    row = analysis.sequence[0]
    assert row.known == 1
    assert set(row.new_deck_chars) == {"二", "三"}
    assert row.activation_deck_chars == ()
    assert analysis.new_deck_chars == {"二", "三"}
    assert analysis.total_days == 1


def test_analyze_song_corpus_tracks_progressive_activation_delta() -> None:
    songs = [
        _song("first", "First", {"一", "二", "三"}),
        _song("second", "Second", {"二", "三", "四"}),
    ]

    analysis = analyze_song_corpus(
        songs,
        active_chars={"一", "四"},
        learned_chars={"一"},
        deck_chars={"一", "二", "三", "四"},
        requested_sequence=["first", "second"],
    )

    first, second = analysis.sequence
    assert set(first.new_deck_chars) == {"二", "三"}
    assert set(first.activation_deck_chars) == {"二", "三"}
    assert set(second.new_deck_chars) == {"四"}
    assert second.activation_deck_chars == ()


def test_plan_song_activation_skips_active_and_non_deck_chars_with_limit() -> None:
    song = _song("cat", "学猫叫", {"一", "二", "三", "喵"})

    plan = plan_song_activation(
        song,
        active_chars={"一"},
        deck_chars={"一", "二", "三"},
        deck_order=["一", "二", "三"],
        limit=1,
    )

    assert plan.chars == ("二",)
    assert plan.remaining_after_limit == ("三",)
    assert plan.already_active == ("一",)
    assert plan.non_deck_chars == ("喵",)


def test_plan_song_activation_normalizes_traditional_particle_to_study_form() -> None:
    song = LyricSong(
        file="cat",
        title="学猫叫",
        artist="",
        lyrics="看著我",
        characters={"看", "著", "我"},
        path=Path("cat.md"),
    )

    plan = plan_song_activation(
        song,
        active_chars={"我", "看"},
        deck_chars={"我", "看", "着"},
        deck_order=["看", "我", "着"],
    )

    assert plan.chars == ("着",)
    assert plan.already_active == ("我", "看")
    assert plan.non_deck_chars == ()


def test_find_song_matches_unique_substring() -> None:
    songs = [_song("01-cat", "学猫叫", {"猫"}), _song("02-moon", "月亮代表我的心", {"月"})]

    assert find_song(songs, "猫") == songs[0]
    assert find_song(songs, "02-moon") == songs[1]
