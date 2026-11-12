"""Show how batching reduces the number of expensive boundary crossings."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from itertools import islice
from typing import TypeVar


Item = TypeVar("Item")


def batched(values: Iterable[Item], size: int) -> Iterator[list[Item]]:
    if size < 1:
        raise ValueError("Batch size must be positive")

    iterator = iter(values)
    while batch := list(islice(iterator, size)):
        yield batch


def count_calls(item_count: int, batch_size: int) -> int:
    return sum(1 for _ in batched(range(item_count), batch_size))


def demonstration() -> None:
    items = list(range(103))
    batches = list(batched(items, 20))

    assert [item for batch in batches for item in batch] == items
    assert len(batches) == 6
    assert count_calls(103, 1) == 103
    assert count_calls(103, 20) == 6

    print("Items: 103")
    print("One-item calls: 103")
    print("Batched calls: 6")


if __name__ == "__main__":
    demonstration()
