"""Tests for the KeywordFixer batch processor."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from anki_chinese.sentences.keyword_fixer import KeywordFixer, _BATCH_SIZE


def _mock_gemini_response(entries: list[dict]) -> MagicMock:
    """Build a mock Gemini response with JSON text."""
    resp = MagicMock()
    resp.text = json.dumps({"entries": entries})
    return resp


def test_fix_batch_returns_keyword_map() -> None:
    """Single chunk returns correct hanzi → meaning mapping."""
    items = [
        ("的", "这是我的中文书。", "This is my Chinese book."),
        ("元", "这个苹果只要五元。", "This apple only costs five yuan."),
    ]
    mock_entries = [
        {"hanzi": "的", "meaning": "possessive particle; marks possession"},
        {"hanzi": "元", "meaning": "first, original; currency unit (yuan)"},
    ]

    with patch("anki_chinese.sentences.keyword_fixer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = _mock_gemini_response(mock_entries)

        fixer = KeywordFixer(api_key="test-key")
        result = fixer.fix_batch(items)

    assert result == {
        "的": "possessive particle; marks possession",
        "元": "first, original; currency unit (yuan)",
    }


def test_fix_batch_splits_into_chunks() -> None:
    """Items exceeding batch size get split into multiple API calls."""
    items = [(f"字{i}", f"句子{i}", f"sentence {i}") for i in range(_BATCH_SIZE + 5)]

    call_count = 0

    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Return empty entries for simplicity
        return _mock_gemini_response([])

    with patch("anki_chinese.sentences.keyword_fixer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = mock_generate

        fixer = KeywordFixer(api_key="test-key")
        fixer.fix_batch(items)

    assert call_count == 2  # 20 + 5


def test_fix_batch_handles_api_error_gracefully() -> None:
    """Non-429 API errors return empty dict for that chunk."""
    items = [("水", "我喝水。", "I drink water.")]

    with patch("anki_chinese.sentences.keyword_fixer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = RuntimeError("server error")

        fixer = KeywordFixer(api_key="test-key")
        result = fixer.fix_batch(items)

    assert result == {}


def test_fix_batch_empty_items() -> None:
    """Empty input returns empty dict without API calls."""
    with patch("anki_chinese.sentences.keyword_fixer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        fixer = KeywordFixer(api_key="test-key")
        result = fixer.fix_batch([])

    assert result == {}
    mock_client.models.generate_content.assert_not_called()
