from __future__ import annotations

import os
from pathlib import Path

from anki_chinese.notes import CharacterNote, save_notes
from anki_chinese.workflows.pipeline_state import record_stage
from anki_chinese.workflows.sync import plan_sync


def _touch(path: Path, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (mtime, mtime))


def _plan(
    tmp_path: Path,
    *,
    valid_tags: set[str] | None = None,
    skip_audio: bool = False,
    pipeline_state_path: Path | None = None,
):
    return plan_sync(
        source_deck_path=tmp_path / "data" / "source" / "deck.apkg",
        overrides_path=tmp_path / "data" / "manual" / "overrides.json",
        enriched_path=tmp_path / "data" / "state" / "enriched.json",
        deck_output_path=tmp_path / "data" / "build" / "decks" / "deck.apkg",
        generated_audio_dir=tmp_path / "data" / "build" / "audio" / "generated",
        is_valid_audio_tag=lambda tag: tag in (valid_tags or set()),
        skip_audio=skip_audio,
        pipeline_state_path=pipeline_state_path,
    )


def _stage_statuses(plan) -> dict[str, str]:
    return {stage.id: stage.status for stage in plan.stages}


def test_plan_requires_init_when_enriched_state_is_missing(tmp_path: Path) -> None:
    _touch(tmp_path / "data" / "source" / "deck.apkg", 100)

    plan = _plan(tmp_path)

    assert _stage_statuses(plan) == {
        "init": "needed",
        "audio": "blocked",
        "build": "blocked",
    }
    assert plan.required_commands == ["anki-chinese init"]


def test_plan_requires_init_when_overrides_are_newer_than_state(tmp_path: Path) -> None:
    _touch(tmp_path / "data" / "source" / "deck.apkg", 100)
    save_notes([CharacterNote(hanzi="一", meaning="one")], tmp_path / "data" / "state" / "enriched.json")
    os.utime(tmp_path / "data" / "state" / "enriched.json", (110, 110))
    _touch(tmp_path / "data" / "manual" / "overrides.json", 120)

    plan = _plan(tmp_path)

    assert _stage_statuses(plan)["init"] == "needed"
    assert plan.stages[0].reason == "Source deck or manual overrides changed after enriched state."


def test_plan_detects_pending_sentence_audio_and_blocks_build_until_audio(tmp_path: Path) -> None:
    _touch(tmp_path / "data" / "source" / "deck.apkg", 100)
    _touch(tmp_path / "data" / "manual" / "overrides.json", 100)
    note = CharacterNote(
        hanzi="水",
        meaning="water",
        pinyin="shuǐ",
        jyutping="seoi2",
        mandarin_audio="[sound:cmn_水_shuǐ.mp3]",
        cantonese_audio="[sound:yue_水_seoi2.mp3]",
        sentence="我喝水。",
        sentence_audio="[sound:cmn_sentence_旧句子.mp3]",
    )
    save_notes([note], tmp_path / "data" / "state" / "enriched.json")
    os.utime(tmp_path / "data" / "state" / "enriched.json", (110, 110))
    _touch(tmp_path / "data" / "build" / "decks" / "deck.apkg", 120)

    plan = _plan(
        tmp_path,
        valid_tags={
            "[sound:cmn_水_shuǐ.mp3]",
            "[sound:yue_水_seoi2.mp3]",
        },
    )

    statuses = _stage_statuses(plan)
    assert statuses["audio"] == "needed"
    assert statuses["build"] == "blocked"
    assert plan.stages[1].details == {
        "pending_notes": 1,
        "mandarin": 0,
        "cantonese": 0,
        "sentence": 1,
    }


def test_plan_requires_build_when_deck_is_missing_after_state_is_ready(tmp_path: Path) -> None:
    _touch(tmp_path / "data" / "source" / "deck.apkg", 100)
    _touch(tmp_path / "data" / "manual" / "overrides.json", 100)
    save_notes([CharacterNote(hanzi="一", meaning="one")], tmp_path / "data" / "state" / "enriched.json")
    os.utime(tmp_path / "data" / "state" / "enriched.json", (110, 110))

    plan = _plan(tmp_path)

    assert _stage_statuses(plan) == {
        "init": "up_to_date",
        "audio": "up_to_date",
        "build": "needed",
    }
    assert plan.required_commands == ["anki-chinese build"]


def test_plan_reports_up_to_date_when_artifacts_are_current(tmp_path: Path) -> None:
    _touch(tmp_path / "data" / "source" / "deck.apkg", 100)
    _touch(tmp_path / "data" / "manual" / "overrides.json", 100)
    save_notes([CharacterNote(hanzi="一", meaning="one")], tmp_path / "data" / "state" / "enriched.json")
    os.utime(tmp_path / "data" / "state" / "enriched.json", (110, 110))
    _touch(tmp_path / "data" / "build" / "decks" / "deck.apkg", 120)

    plan = _plan(tmp_path)

    assert plan.is_up_to_date
    assert plan.required_commands == []


def test_plan_can_skip_audio_and_build_when_deck_is_missing(tmp_path: Path) -> None:
    _touch(tmp_path / "data" / "source" / "deck.apkg", 100)
    _touch(tmp_path / "data" / "manual" / "overrides.json", 100)
    save_notes(
        [CharacterNote(hanzi="一", meaning="one", pinyin="yī")],
        tmp_path / "data" / "state" / "enriched.json",
    )
    os.utime(tmp_path / "data" / "state" / "enriched.json", (110, 110))

    plan = _plan(tmp_path, skip_audio=True)

    assert _stage_statuses(plan) == {
        "init": "up_to_date",
        "audio": "skipped",
        "build": "needed",
    }


def test_plan_reports_current_pipeline_fingerprints(tmp_path: Path) -> None:
    source = tmp_path / "data" / "source" / "deck.apkg"
    overrides = tmp_path / "data" / "manual" / "overrides.json"
    enriched = tmp_path / "data" / "state" / "enriched.json"
    state_path = tmp_path / "data" / "state" / "pipeline.json"
    _touch(source, 100)
    _touch(overrides, 100)
    save_notes([CharacterNote(hanzi="一", meaning="one")], enriched)
    os.utime(enriched, (110, 110))
    record_stage(
        state_path,
        "init",
        inputs={"source_deck": source, "overrides": overrides},
        outputs={"enriched": enriched},
    )

    plan = _plan(tmp_path, pipeline_state_path=state_path)

    init_stage = plan.stages[0]
    assert init_stage.last_completed_at is not None
    assert init_stage.fingerprints_current is True
    assert init_stage.to_dict()["fingerprints_current"] is True


def test_plan_reports_stale_pipeline_fingerprints(tmp_path: Path) -> None:
    source = tmp_path / "data" / "source" / "deck.apkg"
    overrides = tmp_path / "data" / "manual" / "overrides.json"
    enriched = tmp_path / "data" / "state" / "enriched.json"
    state_path = tmp_path / "data" / "state" / "pipeline.json"
    _touch(source, 100)
    _touch(overrides, 100)
    save_notes([CharacterNote(hanzi="一", meaning="one")], enriched)
    os.utime(enriched, (110, 110))
    record_stage(
        state_path,
        "init",
        inputs={"source_deck": source, "overrides": overrides},
        outputs={"enriched": enriched},
    )
    _touch(overrides, 120)

    plan = _plan(tmp_path, pipeline_state_path=state_path)

    assert plan.stages[0].fingerprints_current is False
