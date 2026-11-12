"""Compare repeated list membership with set membership."""

from __future__ import annotations

from statistics import median
from timeit import repeat


def find_common_with_lists(left: list[int], right: list[int]) -> list[int]:
    return [value for value in left if value in right]


def find_common_with_set(left: list[int], right: list[int]) -> list[int]:
    right_lookup = set(right)
    return [value for value in left if value in right_lookup]


def benchmark() -> None:
    left = list(range(2_000))
    right = list(range(1_000, 3_000))

    expected = find_common_with_lists(left, right)
    actual = find_common_with_set(left, right)
    assert actual == expected

    list_times = repeat(
        lambda: find_common_with_lists(left, right),
        number=3,
        repeat=5,
    )
    set_times = repeat(
        lambda: find_common_with_set(left, right),
        number=3,
        repeat=5,
    )

    print(f"List membership median: {median(list_times):.6f}s")
    print(f"Set membership median:  {median(set_times):.6f}s")


if __name__ == "__main__":
    benchmark()
