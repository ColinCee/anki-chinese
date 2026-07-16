from __future__ import annotations

from pathlib import Path

from anki_chinese.character_frequency import (
    FrequencyEntry,
    FrequencySnapshot,
    build_frequency_report,
    load_frequency_snapshot,
    parse_frequency_page,
    save_frequency_snapshot,
)


def test_parse_frequency_page_reads_records_and_metadata() -> None:
    payload = (
        """<html><body>
        <p>Data last updated: 2024-01-02</p>
        <pre>1\t一\t100\t50.0\tyi1\tone<br>2\t不\t80\t90.0\tbu4\tnot<br></pre>
        <h3>Total number of characters in the corpus: 200</h3>
        </body></html>"""
        .encode("gb18030")
    )

    snapshot = parse_frequency_page(payload, retrieved_at="2026-01-01T00:00:00Z")

    assert snapshot.source_last_updated == "2024-01-02"
    assert snapshot.corpus_characters == 200
    assert snapshot.entries[0].character == "一"
    assert snapshot.entries[1].frequency == 80


def test_frequency_snapshot_round_trips(tmp_path: Path) -> None:
    snapshot = FrequencySnapshot(
        source_name="test",
        source_url="https://example.test",
        source_last_updated="2024-01-02",
        retrieved_at="2026-01-01T00:00:00Z",
        corpus_characters=100,
        entries=(
            FrequencyEntry(
                character="一",
                rank=1,
                frequency=100,
                cumulative_percent=100.0,
                pinyin="yi1",
            ),
        ),
    )
    path = tmp_path / "frequency.json"

    save_frequency_snapshot(snapshot, path)

    assert load_frequency_snapshot(path) == snapshot


def test_build_frequency_report_ranks_gaps_and_calculates_coverage() -> None:
    snapshot = FrequencySnapshot(
        source_name="test",
        source_url="https://example.test",
        source_last_updated="2024-01-02",
        retrieved_at="2026-01-01T00:00:00Z",
        corpus_characters=1000,
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
