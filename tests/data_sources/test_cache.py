from unittest.mock import MagicMock

from anki_chinese.data_sources.cache import MemoizedLoader


def test_get_or_load_calls_loader_once():
    loader = MagicMock(return_value="result")
    cache: MemoizedLoader[str, str] = MemoizedLoader()

    cache.get_or_load("k", loader)
    cache.get_or_load("k", loader)

    loader.assert_called_once()


def test_get_or_load_different_keys():
    loader_a = MagicMock(return_value=1)
    loader_b = MagicMock(return_value=2)
    cache: MemoizedLoader[str, int] = MemoizedLoader()

    val_a = cache.get_or_load("a", loader_a)
    val_b = cache.get_or_load("b", loader_b)

    assert val_a == 1
    assert val_b == 2
    loader_a.assert_called_once()
    loader_b.assert_called_once()


def test_clear_resets_cache():
    loader = MagicMock(return_value="v1")
    cache: MemoizedLoader[str, str] = MemoizedLoader()

    cache.get_or_load("k", loader)
    cache.clear()

    loader.return_value = "v2"
    assert cache.get_or_load("k", loader) == "v2"
    assert loader.call_count == 2


def test_get_or_load_returns_loader_value():
    cache: MemoizedLoader[str, str] = MemoizedLoader()

    result = cache.get_or_load("key", lambda: "hello")

    assert result == "hello"
