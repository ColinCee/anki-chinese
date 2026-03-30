"""Small cache helpers for data-source services."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class MemoizedLoader[K, V]:
    _values: dict[K, V] = field(default_factory=dict)

    def get_or_load(self, key: K, loader: Callable[[], V]) -> V:
        if key not in self._values:
            self._values[key] = loader()
        return self._values[key]

    def clear(self) -> None:
        self._values.clear()
