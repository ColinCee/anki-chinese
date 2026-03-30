from unittest.mock import MagicMock

from anki_chinese.data_sources.cache import MemoizedLoader


def test_get_or_load_caches_after_first_call():
    loader = MagicMock(return_value="result")
    cache: MemoizedLoader[str, str] = MemoizedLoader()

    first = cache.get_or_load("k", loader)
    second = cache.get_or_load("k", loader)

    assert first == second == "result"
    loader.assert_called_once()


def test_clear_removes_cached_values():
    loader = MagicMock(return_value="v1")
    cache: MemoizedLoader[str, str] = MemoizedLoader()

    cache.get_or_load("k", loader)
    cache.clear()

    loader.return_value = "v2"
    assert cache.get_or_load("k", loader) == "v2"
    assert loader.call_count == 2


def test_different_keys_cached_independently():
    cache: MemoizedLoader[str, int] = MemoizedLoader()

    val_a = cache.get_or_load("a", lambda: 1)
    val_b = cache.get_or_load("b", lambda: 2)

    assert val_a == 1
    assert val_b == 2
