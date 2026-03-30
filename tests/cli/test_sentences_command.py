"""Tests for the `anki-chinese sentences` CLI command."""

from __future__ import annotations

from unittest.mock import patch

from anki_chinese.cli.sentences import apply_sentence, run_sentences
from anki_chinese.notes import CharacterNote
from anki_chinese.sentences.generator import SentenceResult


def _make_result(hanzi: str, *, valid: bool = True, error: str = "") -> SentenceResult:
    return SentenceResult(
        sentence=f"我有{hanzi}。",
        pinyin="wǒ yǒu...",
        english=f"I have {hanzi}.",
        keyword="test",
        valid=valid,
        error=error,
    )


class TestFiltering:
    def test_skips_notes_with_existing_sentence(self, runtime_factory):
        notes = [
            CharacterNote(hanzi="一", keyword="one", sentence="已有句子"),
            CharacterNote(hanzi="二", keyword="two"),
        ]
        runtime = runtime_factory(saved_notes=notes)

        with patch("anki_chinese.sentences.SentenceGenerator") as MockGen:
            mock_gen = MockGen.return_value
            mock_gen.generate.return_value = _make_result("二")
            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
                run_sentences(runtime, force=False)

        # Only called for 二 (一 already has a sentence)
        mock_gen.generate.assert_called_once_with("二")

    def test_force_regenerates_all(self, runtime_factory):
        notes = [
            CharacterNote(hanzi="一", keyword="one", sentence="已有句子"),
            CharacterNote(hanzi="二", keyword="two", sentence="也有了"),
        ]
        runtime = runtime_factory(saved_notes=notes)

        with patch("anki_chinese.sentences.SentenceGenerator") as MockGen:
            mock_gen = MockGen.return_value
            mock_gen.generate.side_effect = [_make_result("一"), _make_result("二")]
            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
                run_sentences(runtime, force=True)

        assert mock_gen.generate.call_count == 2

    def test_char_filter_targets_single_note(self, runtime_factory):
        notes = [
            CharacterNote(hanzi="一", keyword="one"),
            CharacterNote(hanzi="二", keyword="two"),
            CharacterNote(hanzi="三", keyword="three"),
        ]
        runtime = runtime_factory(saved_notes=notes)

        with patch("anki_chinese.sentences.SentenceGenerator") as MockGen:
            mock_gen = MockGen.return_value
            mock_gen.generate.return_value = _make_result("二")
            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
                run_sentences(runtime, char="二")

        mock_gen.generate.assert_called_once_with("二")

    def test_limit_caps_number_processed(self, runtime_factory):
        notes = [
            CharacterNote(hanzi="一", keyword="one"),
            CharacterNote(hanzi="二", keyword="two"),
            CharacterNote(hanzi="三", keyword="three"),
        ]
        runtime = runtime_factory(saved_notes=notes)

        with patch("anki_chinese.sentences.SentenceGenerator") as MockGen:
            mock_gen = MockGen.return_value
            mock_gen.generate.side_effect = [_make_result("一"), _make_result("二")]
            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
                run_sentences(runtime, limit=2)

        assert mock_gen.generate.call_count == 2


class TestAPIKeyMissing:
    def test_warns_and_returns_early_without_api_key(self, runtime_factory):
        notes = [CharacterNote(hanzi="一", keyword="one")]
        runtime = runtime_factory(saved_notes=notes)

        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            run_sentences(runtime)

        console_output = runtime.console.file.getvalue()  # type: ignore[union-attr]
        assert "GEMINI_API_KEY" in console_output


class TestResultPopulation:
    def test_populates_all_sentence_fields_on_note(self, runtime_factory):
        notes = [CharacterNote(hanzi="水", keyword="water")]
        runtime = runtime_factory(saved_notes=notes)

        result = SentenceResult(
            sentence="我喝水。",
            pinyin="wǒ hē shuǐ.",
            english="I drink water.",
            keyword="water",
            valid=True,
        )

        with patch("anki_chinese.sentences.SentenceGenerator") as MockGen:
            MockGen.return_value.generate.return_value = result
            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
                run_sentences(runtime)

        saved = runtime.note_store.load()
        note = saved[0]
        assert note.sentence == "我喝水。"
        assert note.sentence_pinyin == "wǒ hē shuǐ."
        assert note.sentence_english == "I drink water."
        assert note.keyword == "water"  # sentence_keyword merged into keyword

    def test_saves_to_store_after_generation(self, runtime_factory):
        notes = [CharacterNote(hanzi="水", keyword="water")]
        runtime = runtime_factory(saved_notes=notes)

        with patch("anki_chinese.sentences.SentenceGenerator") as MockGen:
            MockGen.return_value.generate.return_value = _make_result("水")
            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
                run_sentences(runtime)

        # Verify data was persisted
        reloaded = runtime.note_store.load()
        assert reloaded[0].sentence != ""


class TestErrorCounting:
    def test_counts_failures_from_invalid_results(self, runtime_factory):
        notes = [
            CharacterNote(hanzi="一", keyword="one"),
            CharacterNote(hanzi="二", keyword="two"),
        ]
        runtime = runtime_factory(saved_notes=notes)

        results = [
            _make_result("一", valid=True),
            _make_result("二", valid=False, error="target char missing"),
        ]

        with patch("anki_chinese.sentences.SentenceGenerator") as MockGen:
            MockGen.return_value.generate.side_effect = results
            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
                run_sentences(runtime)

        output = runtime.console.file.getvalue()  # type: ignore[union-attr]
        assert "1" in output  # at least "Generated 1"

    def test_counts_exceptions_as_failures(self, runtime_factory):
        notes = [CharacterNote(hanzi="一", keyword="one")]
        runtime = runtime_factory(saved_notes=notes)

        with patch("anki_chinese.sentences.SentenceGenerator") as MockGen:
            MockGen.return_value.generate.side_effect = Exception("API down")
            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
                run_sentences(runtime)

        output = runtime.console.file.getvalue()  # type: ignore[union-attr]
        assert "failed" in output.lower() or "✗" in output


class TestAllSentencesExist:
    def test_prints_already_done_message(self, runtime_factory):
        notes = [CharacterNote(hanzi="一", keyword="one", sentence="有了")]
        runtime = runtime_factory(saved_notes=notes)

        with (
            patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}),
            patch("anki_chinese.sentences.SentenceGenerator"),
        ):
            run_sentences(runtime)

        output = runtime.console.file.getvalue()  # type: ignore[union-attr]
        assert "already have" in output.lower()


class TestApplySentence:
    def test_writes_all_fields_to_note(self):
        note = CharacterNote(hanzi="水", keyword="old")
        result = SentenceResult(
            sentence="我喝水。", pinyin="wǒ hē shuǐ.",
            english="I drink water.", keyword="water", valid=True,
        )

        apply_sentence(note, result)

        assert note.sentence == "我喝水。"
        assert note.sentence_pinyin == "wǒ hē shuǐ."
        assert note.sentence_english == "I drink water."
        assert note.keyword == "water"

    def test_clears_stale_audio(self):
        note = CharacterNote(
            hanzi="水", keyword="water",
            sentence_audio="[sound:cmn_sentence_old.mp3]",
        )
        result = SentenceResult(
            sentence="新句子。", pinyin="xīn jùzi.",
            english="New sentence.", keyword="water", valid=True,
        )

        apply_sentence(note, result)

        assert note.sentence_audio == ""

    def test_preserves_keyword_when_result_keyword_empty(self):
        note = CharacterNote(hanzi="水", keyword="water")
        result = SentenceResult(
            sentence="我喝水。", pinyin="wǒ hē shuǐ.",
            english="I drink water.", keyword="", valid=True,
        )

        apply_sentence(note, result)

        assert note.keyword == "water"


class TestPickMode:
    def test_pick_populates_chosen_candidate(self, runtime_factory):
        notes = [CharacterNote(hanzi="水", keyword="water")]
        runtime = runtime_factory(saved_notes=notes)

        candidates = [
            SentenceResult(sentence="我喝水。", pinyin="wǒ hē shuǐ.",
                           english="I drink water.", keyword="water", valid=True),
            SentenceResult(sentence="水很冷。", pinyin="shuǐ hěn lěng.",
                           english="The water is cold.", keyword="water", valid=True),
        ]

        with patch("anki_chinese.sentences.SentenceGenerator") as MockGen:
            MockGen.return_value.generate_candidates.return_value = candidates
            with (
                patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}),
                patch("typer.prompt", return_value="2"),
            ):
                run_sentences(runtime, char="水", pick=2)

        saved = runtime.note_store.load()
        assert saved[0].sentence == "水很冷。"
        assert saved[0].sentence_audio == ""  # cleared for regeneration

    def test_pick_skip_leaves_note_unchanged(self, runtime_factory):
        notes = [CharacterNote(hanzi="水", keyword="water", sentence="原来的。")]
        runtime = runtime_factory(saved_notes=notes)

        candidates = [
            SentenceResult(sentence="新的。", pinyin="xīn de.",
                           english="New.", keyword="water", valid=True),
        ]

        with patch("anki_chinese.sentences.SentenceGenerator") as MockGen:
            MockGen.return_value.generate_candidates.return_value = candidates
            with (
                patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}),
                patch("typer.prompt", return_value="s"),
            ):
                run_sentences(runtime, char="水", pick=1)

        saved = runtime.note_store.load()
        assert saved[0].sentence == "原来的。"

    def test_pick_no_candidates_does_not_crash(self, runtime_factory):
        notes = [CharacterNote(hanzi="水", keyword="water")]
        runtime = runtime_factory(saved_notes=notes)

        with patch("anki_chinese.sentences.SentenceGenerator") as MockGen:
            MockGen.return_value.generate_candidates.return_value = []
            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
                run_sentences(runtime, char="水", pick=3)

        output = runtime.console.file.getvalue()  # type: ignore[union-attr]
        assert "No valid candidates" in output
