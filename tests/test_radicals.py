from __future__ import annotations

import json
from pathlib import Path

from anki_chinese.notes import CharacterNote
from anki_chinese.radicals import analyze_radical_exposure


def test_analyze_radical_exposure_counts_exact_and_first_character_hsk_matches(
    tmp_path: Path,
) -> None:
    hsk_path = tmp_path / "hsk_complete.min.json"
    hsk_path.write_text(
        json.dumps(
            [
                {"s": "河", "r": "氵"},
                {"s": "清", "r": "氵"},
                {"s": "妈", "r": "女"},
                {"s": "想", "r": "心"},
                {"s": "湖水", "r": "氵"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    notes = [
        CharacterNote(hanzi="河"),
        CharacterNote(hanzi="清"),
        CharacterNote(hanzi="湖"),
        CharacterNote(hanzi="妈"),
        CharacterNote(hanzi="想"),
    ]

    report = analyze_radical_exposure(notes, hsk_path, min_seen=2)

    assert [row.radical for row in report.rows] == ["氵"]
    row = report.rows[0]
    assert row.count == 3
    assert row.nickname == "三点水 sān diǎn shuǐ"
    assert row.priority == "learn now"
    assert row.examples == ("河", "清", "湖")
