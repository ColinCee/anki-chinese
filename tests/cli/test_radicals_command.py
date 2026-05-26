from __future__ import annotations

import json

from anki_chinese.cli import create_app
from anki_chinese.notes import CharacterNote


def test_radicals_command_prints_study_table(runtime_factory, runner) -> None:
    runtime = runtime_factory(
        saved_notes=[
            CharacterNote(hanzi="河"),
            CharacterNote(hanzi="清"),
            CharacterNote(hanzi="湖"),
            CharacterNote(hanzi="妈"),
        ]
    )
    runtime.hsk_vocab_path.parent.mkdir(parents=True, exist_ok=True)
    runtime.hsk_vocab_path.write_text(
        json.dumps(
            [
                {"s": "河", "r": "氵"},
                {"s": "清", "r": "氵"},
                {"s": "湖水", "r": "氵"},
                {"s": "妈", "r": "女"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    app = create_app(runtime)

    result = runner.invoke(app, ["radicals", "--min-seen", "2"])

    assert result.exit_code == 0
    output = runtime.console.file.getvalue()
    assert "三点水 sān diǎn shuǐ" in output
    assert "learn now" in output
    assert "河 清 湖" in output


def test_radicals_command_can_scope_to_learned_characters(runtime_factory, runner) -> None:
    runtime = runtime_factory(
        saved_notes=[
            CharacterNote(hanzi="河"),
            CharacterNote(hanzi="清"),
            CharacterNote(hanzi="妈"),
        ]
    )
    runtime.hsk_vocab_path.parent.mkdir(parents=True, exist_ok=True)
    runtime.hsk_vocab_path.write_text(
        json.dumps(
            [
                {"s": "河", "r": "氵"},
                {"s": "清", "r": "氵"},
                {"s": "妈", "r": "女"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    runtime.load_learned_hanzi = lambda path: {"河", "清"}
    app = create_app(runtime)

    result = runner.invoke(app, ["radicals", "--scope", "learned"])

    assert result.exit_code == 0
    output = runtime.console.file.getvalue()
    assert "三点水 sān diǎn shuǐ" in output
    assert "女字旁" not in output
