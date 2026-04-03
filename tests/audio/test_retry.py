from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, patch

import pytest

from anki_chinese.audio.errors import TTSError, TTSRateLimitError
from anki_chinese.audio.retry import DEFAULT_RETRY_POLICY, RetryPolicy, synthesize_with_retry


def test_default_retry_policy_values_are_stable() -> None:
    assert (
        RetryPolicy(
            rate_limit_retry_delay=30.0,
            max_attempts=5,
        )
        == DEFAULT_RETRY_POLICY
    )


def test_retry_policy_is_frozen() -> None:
    policy = RetryPolicy()

    with pytest.raises(FrozenInstanceError):
        policy.max_attempts = 3


# ---------------------------------------------------------------------------
# synthesize_with_retry
# ---------------------------------------------------------------------------

FAKE_AUDIO = b"ID3fake-audio-bytes"


def _make_rate_limiter() -> MagicMock:
    rl = MagicMock()
    rl.acquire = MagicMock(return_value=None)
    return rl


def test_successful_synthesis_on_first_try(tmp_path):
    output_path = tmp_path / "audio" / "test.mp3"
    synthesize = MagicMock(return_value=FAKE_AUDIO)

    synthesize_with_retry(
        synthesize=synthesize,
        output_path=output_path,
        retry_policy=RetryPolicy(rate_limit_retry_delay=0, max_attempts=3),
        rate_limiter=_make_rate_limiter(),
        provider_name="test",
    )

    synthesize.assert_called_once()
    assert output_path.read_bytes() == FAKE_AUDIO


@patch("anki_chinese.audio.retry.time.sleep")
def test_rate_limit_retries_then_raises(mock_sleep, tmp_path):
    output_path = tmp_path / "test.mp3"
    synthesize = MagicMock(side_effect=TTSRateLimitError("rate limited"))
    policy = RetryPolicy(rate_limit_retry_delay=0, max_attempts=3)

    with pytest.raises(TTSRateLimitError, match="after 3 attempts"):
        synthesize_with_retry(
            synthesize=synthesize,
            output_path=output_path,
            retry_policy=policy,
            rate_limiter=_make_rate_limiter(),
            provider_name="test",
        )

    assert synthesize.call_count == 3


def test_non_rate_limit_tts_error_raises_immediately(tmp_path):
    output_path = tmp_path / "test.mp3"
    synthesize = MagicMock(side_effect=TTSError("bad request"))

    with pytest.raises(TTSError, match="bad request"):
        synthesize_with_retry(
            synthesize=synthesize,
            output_path=output_path,
            retry_policy=RetryPolicy(rate_limit_retry_delay=0, max_attempts=5),
            rate_limiter=_make_rate_limiter(),
            provider_name="test",
        )

    synthesize.assert_called_once()


@patch("anki_chinese.audio.retry.time.sleep")
def test_cleanup_called_on_errors(mock_sleep, tmp_path):
    output_path = tmp_path / "test.mp3"
    synthesize = MagicMock(side_effect=TTSRateLimitError("rate limited"))
    cleanup = MagicMock()
    policy = RetryPolicy(rate_limit_retry_delay=0, max_attempts=2)

    with pytest.raises(TTSRateLimitError):
        synthesize_with_retry(
            synthesize=synthesize,
            output_path=output_path,
            retry_policy=policy,
            rate_limiter=_make_rate_limiter(),
            provider_name="test",
            cleanup=cleanup,
        )

    # cleanup is called before each attempt and again after each error
    assert cleanup.call_count >= 2


@patch("anki_chinese.audio.retry.is_valid_audio_file", return_value=False)
def test_invalid_audio_file_raises_tts_error(mock_valid, tmp_path):
    output_path = tmp_path / "test.mp3"
    synthesize = MagicMock(return_value=FAKE_AUDIO)

    with pytest.raises(TTSError, match="did not create audio"):
        synthesize_with_retry(
            synthesize=synthesize,
            output_path=output_path,
            retry_policy=RetryPolicy(rate_limit_retry_delay=0, max_attempts=1),
            rate_limiter=_make_rate_limiter(),
            provider_name="test",
        )
