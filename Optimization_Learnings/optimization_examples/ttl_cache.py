"""A small TTL cache with injectable time for deterministic testing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Generic, TypeVar


Key = TypeVar("Key")
Value = TypeVar("Value")


@dataclass
class CacheEntry(Generic[Value]):
    value: Value
    expires_at: float


class TTLCache(Generic[Key, Value]):
    def __init__(
        self,
        ttl_seconds: float,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self.entries: dict[Key, CacheEntry[Value]] = {}

    def get_or_load(self, key: Key, loader: Callable[[], Value]) -> Value:
        now = self.clock()
        entry = self.entries.get(key)

        if entry is not None and entry.expires_at > now:
            return entry.value

        value = loader()
        self.entries[key] = CacheEntry(value, now + self.ttl_seconds)
        return value

    def invalidate(self, key: Key) -> None:
        self.entries.pop(key, None)


def demonstration() -> None:
    current_time = [0.0]
    loads = [0]
    cache: TTLCache[str, str] = TTLCache(5, lambda: current_time[0])

    def load_user() -> str:
        loads[0] += 1
        return f"user-version-{loads[0]}"

    assert cache.get_or_load("user:1", load_user) == "user-version-1"
    assert cache.get_or_load("user:1", load_user) == "user-version-1"
    assert loads[0] == 1

    current_time[0] = 6.0
    assert cache.get_or_load("user:1", load_user) == "user-version-2"
    assert loads[0] == 2

    cache.invalidate("user:1")
    assert cache.get_or_load("user:1", load_user) == "user-version-3"
    print("TTL, cache hit, expiry, and invalidation checks passed")


if __name__ == "__main__":
    demonstration()
