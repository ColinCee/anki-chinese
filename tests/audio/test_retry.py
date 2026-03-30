from dataclasses import FrozenInstanceError

import pytest

from anki_chinese.audio.retry import DEFAULT_RETRY_POLICY, RetryPolicy


def test_default_retry_policy_values_are_stable() -> None:
    assert RetryPolicy(
        rate_limit_retry_delay=30.0,
        max_attempts=5,
    ) == DEFAULT_RETRY_POLICY


def test_retry_policy_is_frozen() -> None:
    policy = RetryPolicy()

    with pytest.raises(FrozenInstanceError):
        policy.max_attempts = 3
