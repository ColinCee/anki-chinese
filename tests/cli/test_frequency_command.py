from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from anki_chinese.activation import AnkiConnectError
from anki_chinese.character_frequency import (
    FrequencyEntry,
    FrequencySnapshot,
    save_frequency_snapshot,
)
from anki_chinese.cli.frequency import run_frequency_report


class StubFrequencyClient:
    def find_studied_characters(self) -> set[str]:
        return {"一"}

    def find_all_deck_info(self) -> tuple[list[str], set[str]]:
        return ["一", "不"], {"一", "不"}


def _write_snapshot(path: Path) -> None:
    save_frequency_snapshot(
        FrequencySnapshot(
            source_name="test",
            source_url="https://example.test",
            source_last_updated="2024-01-02",
            retrieved_at="2026-01-01T00:00:00Z",
            corpus_characters=1000,
            entries=(
                FrequencyEntry("一", 1, 500, 50.0, "yi1"),
                FrequencyEntry("不", 2, 300, 80.0, "bu4"),
            ),
        ),
        path,
    )


def test_frequency_report_json_is_agent_readable(runtime_factory, tmp_path: Path) -> None:
    runtime = runtime_factory()
    cache_path = tmp_path / "frequency.json"
    _write_snapshot(cache_path)

    run_frequency_report(
        runtime,
        cache_path=cache_path,
        client=StubFrequencyClient(),
        json_output=True,
    )

    data = json.loads(runtime.console.file.getvalue())
    assert data["studied_count"] == 1
    assert data["top_frequency_gaps"][0]["character"] == "不"
    assert data["covered_characters"][0]["character"] == "一"
    assert data["top_rank_deck_counts"]["100"] == {
        "reviewed": 1,
        "unreviewed": 1,
        "in_deck": 2,
    }


def test_frequency_report_human_output_explains_progress(runtime_factory, tmp_path: Path) -> None:
    runtime = runtime_factory()
    cache_path = tmp_path / "frequency.json"
    _write_snapshot(cache_path)

    run_frequency_report(
        runtime,
        cache_path=cache_path,
        client=StubFrequencyClient(),
    )

    output = runtime.console.file.getvalue()
    assert "Top-N coverage" in output
    assert "Cumulative source share" in output
    assert "Impact of learning next 1" in output
    assert "Potential gain" in output
    assert "Frequency score" not in output


def test_frequency_report_surfaces_anki_errors(runtime_factory, tmp_path: Path) -> None:
    class BrokenClient(StubFrequencyClient):
        def find_studied_characters(self) -> set[str]:
            raise AnkiConnectError("offline")

    runtime = runtime_factory()
    cache_path = tmp_path / "frequency.json"
    _write_snapshot(cache_path)

    with pytest.raises(typer.Exit) as error:
        run_frequency_report(runtime, cache_path=cache_path, client=BrokenClient())
    assert error.value.exit_code == 2
    assert "offline" in runtime.console.file.getvalue()
