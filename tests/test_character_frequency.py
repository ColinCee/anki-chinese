from __future__ import annotations

from pathlib import Path

import pytest

from anki_chinese.character_frequency import (
    FrequencyDataError,
    FrequencyEntry,
    FrequencySnapshot,
    build_frequency_report,
    build_wordfreq_snapshot,
    load_frequency_snapshot,
    save_frequency_snapshot,
)


def test_build_wordfreq_snapshot_scores_hanzi_occurrences() -> None:
    words = ["中国", "中国人", "的", "ABC", "人间"]
    frequencies = {
        "中国": 0.8,
        "中国人": 0.4,
        "的": 0.7,
        "人间": 0.2,
    }

    snapshot = build_wordfreq_snapshot(
        word_limit=4,
        words=words,
        frequency_lookup=lambda word: frequencies[word],
        retrieved_at="2026-01-01T00:00:00Z",
    )

    assert snapshot.source_name == "wordfreq Chinese large word list"
    assert snapshot.corpus_characters is None
    assert snapshot.parameters["words_seen"] == 4
    assert snapshot.parameters["hanzi_words_used"] == 3
    assert [entry.character for entry in snapshot.entries] == ["中", "国", "的", "人"]
    assert [entry.frequency for entry in snapshot.entries] == pytest.approx([1.2, 1.2, 0.7, 0.4])


def test_frequency_snapshot_round_trips(tmp_path: Path) -> None:
    snapshot = FrequencySnapshot(
        source_name="test",
        source_url="https://example.test",
        source_last_updated="2024-01-02",
        retrieved_at="2026-01-01T00:00:00Z",
        corpus_characters=None,
        entries=(
            FrequencyEntry(
                character="一",
                rank=1,
                frequency=100.5,
                cumulative_percent=100.0,
                pinyin="yi1",
            ),
        ),
    )
    path = tmp_path / "frequency.json"

    save_frequency_snapshot(snapshot, path)

    assert load_frequency_snapshot(path) == snapshot


def test_frequency_snapshot_rejects_non_finite_scores(tmp_path: Path) -> None:
    path = tmp_path / "frequency.json"
    path.write_text(
        """{
          "schema_version": 2,
          "source": {
            "name": "test",
            "url": "https://example.test",
            "last_updated": "2024-01-02",
            "retrieved_at": "2026-01-01T00:00:00Z"
          },
          "corpus_characters": null,
          "entries": [{
            "character": "一",
            "rank": 1,
            "frequency": NaN,
            "cumulative_percent": 100.0
          }]
        }""",
        encoding="utf-8",
    )

    with pytest.raises(FrequencyDataError, match="invalid entry values"):
        load_frequency_snapshot(path)


def test_build_frequency_report_ranks_gaps_and_calculates_coverage() -> None:
    snapshot = FrequencySnapshot(
        source_name="test",
        source_url="https://example.test",
        source_last_updated="2024-01-02",
        retrieved_at="2026-01-01T00:00:00Z",
        corpus_characters=None,
        entries=(
            FrequencyEntry("一", 1, 500, 50.0, "yi1"),
            FrequencyEntry("不", 2, 300, 80.0, "bu4"),
            FrequencyEntry("人", 3, 200, 100.0, "ren2"),
        ),
    )

    report = build_frequency_report(
        snapshot,
        studied_characters={"一", "中国"},
        deck_characters={"一", "不", "人", "龘"},
        limit=2,
    )

    assert report.studied_count == 1
    assert report.corpus_coverage_percent == 50.0
    assert report.deck_coverage_percent == 25.0
    assert [entry.character for entry in report.gap_entries] == ["不", "人"]
    assert report.unranked_gap_count == 1
    assert report.studied_unranked_count == 0
    assert report.top_rank_deck_counts[0] == (100, 1, 2, 3)
