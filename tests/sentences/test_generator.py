"""Tests for SentenceGenerator — all Gemini calls mocked."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from anki_chinese.sentences.generator import (
    SentenceGenerator,
    SentenceResult,
)


def _sentence_json(sentence: str = "我喝一杯咖啡。", **overrides) -> str:
    data = {
        "sentence": sentence,
        "pinyin": overrides.get("pinyin", "wǒ hē yī bēi kāfēi."),
        "english": overrides.get("english", "I drink a cup of coffee."),
        "meaning": overrides.get("meaning", "one"),
        "character_pinyin": overrides.get("character_pinyin", "yī"),
    }
    return json.dumps(data)


def _validation_json(*, grammar_correct: bool = True, natural: bool = True, error: str = "") -> str:
    return json.dumps({
        "grammar_correct": grammar_correct,
        "natural": natural,
        "error_description": error,
    })


def _mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


class TestHappyPath:
    """Character present + validation passes → clean result."""

    def test_generate_returns_valid_result(self):
        gen = SentenceGenerator(api_key="fake")
        responses = [
            _mock_response(_sentence_json("我喝一杯咖啡。")),
            _mock_response(_validation_json()),
        ]
        gen._client = MagicMock()
        gen._client.models.generate_content = MagicMock(side_effect=responses)

        result = gen.generate("一")

        assert result.valid is True
        assert result.error == ""
        assert "一" in result.sentence
        assert result.pinyin != ""
        assert result.english != ""
        assert result.meaning == "one"

    def test_generate_makes_two_api_calls(self):
        gen = SentenceGenerator(api_key="fake")
        responses = [
            _mock_response(_sentence_json("我喝一杯咖啡。")),
            _mock_response(_validation_json()),
        ]
        gen._client = MagicMock()
        gen._client.models.generate_content = MagicMock(side_effect=responses)

        gen.generate("一")

        assert gen._client.models.generate_content.call_count == 2


class TestCharCheckRetries:
    """Character missing from sentence → retry up to 2 times."""

    def test_retries_when_char_missing_then_succeeds(self):
        gen = SentenceGenerator(api_key="fake")
        responses = [
            # First attempt: missing 行
            _mock_response(_sentence_json("我去银行了。", meaning="go")),
            # Wait — that has 行. Use a sentence WITHOUT the char.
        ]
        # Let's use a char that's harder to accidentally include
        responses = [
            _mock_response(_sentence_json("我去学校了。", meaning="big")),  # missing 大
            _mock_response(_sentence_json("这个很大。", meaning="big")),    # has 大
            _mock_response(_validation_json()),
        ]
        gen._client = MagicMock()
        gen._client.models.generate_content = MagicMock(side_effect=responses)

        result = gen.generate("大")

        assert result.valid is True
        assert "大" in result.sentence
        # 3 calls: gen, retry-gen, validate
        assert gen._client.models.generate_content.call_count == 3

    def test_returns_error_after_max_retries_exhausted(self):
        gen = SentenceGenerator(api_key="fake")
        # 3 attempts (1 + 2 retries), all missing the char
        responses = [
            _mock_response(_sentence_json("我去学校。", meaning="big")),
            _mock_response(_sentence_json("他很高。", meaning="big")),
            _mock_response(_sentence_json("这很好。", meaning="big")),
        ]
        gen._client = MagicMock()
        gen._client.models.generate_content = MagicMock(side_effect=responses)

        result = gen.generate("大")

        assert result.valid is False
        assert "missing" in result.error
        assert result.sentence == ""


class TestValidationFlagging:
    """Validation flags error → returns sentence marked invalid for review."""

    def test_flags_invalid_on_validation_failure(self):
        gen = SentenceGenerator(api_key="fake")
        responses = [
            # Initial generation — contains 两
            _mock_response(_sentence_json("我有两个朋友。", meaning="two")),
            # Validation: grammar error
            _mock_response(_validation_json(grammar_correct=False, error="sounds awkward")),
        ]
        gen._client = MagicMock()
        gen._client.models.generate_content = MagicMock(side_effect=responses)

        result = gen.generate("两")

        assert result.valid is False
        assert result.error == "sounds awkward"
        assert "两" in result.sentence  # sentence still returned

    def test_returns_valid_when_validation_passes(self):
        gen = SentenceGenerator(api_key="fake")
        responses = [
            _mock_response(_sentence_json("他在二楼住。", meaning="two")),
            _mock_response(_validation_json()),
        ]
        gen._client = MagicMock()
        gen._client.models.generate_content = MagicMock(side_effect=responses)

        result = gen.generate("二")

        assert result.valid is True
        assert result.sentence != ""


class TestAPIErrorHandling:
    """Rate limits and other errors → graceful degradation."""

    def test_rate_limit_429_returns_none_from_call(self):
        gen = SentenceGenerator(api_key="fake")
        gen._client = MagicMock()
        gen._client.models.generate_content = MagicMock(
            side_effect=Exception("429 Resource has been exhausted")
        )

        # All 3 char-check attempts return None → error
        result = gen.generate("大")

        assert result.valid is False
        assert "missing" in result.error

    def test_generic_api_error_returns_none_from_call(self):
        gen = SentenceGenerator(api_key="fake")
        gen._client = MagicMock()
        gen._client.models.generate_content = MagicMock(
            side_effect=Exception("Connection refused")
        )

        result = gen.generate("大")

        assert result.valid is False

    def test_validation_api_failure_treated_as_pass(self):
        """If validation call fails, we accept the generated sentence."""
        gen = SentenceGenerator(api_key="fake")
        responses = [
            _mock_response(_sentence_json("这个很大。", meaning="big")),
            Exception("timeout"),  # validation fails
        ]
        gen._client = MagicMock()
        gen._client.models.generate_content = MagicMock(side_effect=responses)

        result = gen.generate("大")

        assert result.valid is True
        assert "大" in result.sentence


class TestSentenceResult:
    def test_frozen_dataclass(self):
        r = SentenceResult("你好", "nǐ hǎo", "hello", "good", "nǐ", valid=True)
        with pytest.raises(AttributeError):
            r.sentence = "changed"  # type: ignore[misc]


class TestGenerateCandidates:
    def test_returns_multiple_independent_results(self):
        gen = SentenceGenerator(api_key="fake")
        sentences = ["他很大。", "大家好。", "这个很大。"]
        responses = []
        for s in sentences:
            responses.append(_mock_response(_sentence_json(s, meaning="big")))
            responses.append(_mock_response(_validation_json()))
        gen._client = MagicMock()
        gen._client.models.generate_content = MagicMock(side_effect=responses)

        candidates = gen.generate_candidates("大", count=3)

        assert len(candidates) == 3
        assert {c.sentence for c in candidates} == set(sentences)

    def test_skips_empty_results(self):
        gen = SentenceGenerator(api_key="fake")
        # First call succeeds, second fails (all API errors)
        responses = [
            _mock_response(_sentence_json("他很大。", meaning="big")),
            _mock_response(_validation_json()),
        ]
        gen._client = MagicMock()
        gen._client.models.generate_content = MagicMock(
            side_effect=responses + [Exception("fail")] * 10
        )

        candidates = gen.generate_candidates("大", count=2)

        assert len(candidates) == 1
        assert candidates[0].sentence == "他很大。"

    def test_defaults(self):
        r = SentenceResult("x", "x", "x", "x", "x", valid=True)
        assert r.error == ""
