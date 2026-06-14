from __future__ import annotations

from unittest.mock import patch

from anki_chinese.cli.keywords import run_keywords
from anki_chinese.notes import CharacterNote
from anki_chinese.workflows.pipeline_state import load_pipeline_state


def test_run_keywords_records_pipeline_state_when_meanings_change(runtime_factory) -> None:
    runtime = runtime_factory(
        saved_notes=[
            CharacterNote(
                hanzi="水",
                meaning="old",
                sentence="我喝水。",
                sentence_english="I drink water.",
            )
        ]
    )

    with patch("anki_chinese.sentences.KeywordFixer") as MockFixer:
        MockFixer.return_value.fix_batch.return_value = {"水": "water"}
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
            run_keywords(runtime)

    state = load_pipeline_state(runtime.pipeline_state_path)
    assert "keywords" in state.stages
    assert runtime.note_store.load()[0].meaning == "water"


def test_run_keywords_does_not_record_pipeline_state_when_nothing_changes(runtime_factory) -> None:
    runtime = runtime_factory(
        saved_notes=[
            CharacterNote(
                hanzi="水",
                meaning="water",
                sentence="我喝水。",
                sentence_english="I drink water.",
            )
        ]
    )

    with patch("anki_chinese.sentences.KeywordFixer") as MockFixer:
        MockFixer.return_value.fix_batch.return_value = {"水": "water"}
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
            run_keywords(runtime)

    state = load_pipeline_state(runtime.pipeline_state_path)
    assert "keywords" not in state.stages
