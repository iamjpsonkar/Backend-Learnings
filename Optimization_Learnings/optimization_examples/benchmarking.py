"""Demonstrate repeatable microbenchmark structure with correctness checks."""

from __future__ import annotations

from statistics import median
from timeit import repeat


def normalize_loop(values: list[str]) -> list[str]:
    normalized = []
    for value in values:
        normalized.append(value.strip().lower())
    return normalized


def normalize_comprehension(values: list[str]) -> list[str]:
    return [value.strip().lower() for value in values]


def measure(function, values: list[str]) -> float:
    samples = repeat(lambda: function(values), number=1_000, repeat=7)
    return median(samples)


def main() -> None:
    values = [" Alpha ", "BETA ", " Gamma", "DELTA"] * 25
    assert normalize_loop(values) == normalize_comprehension(values)

    loop_time = measure(normalize_loop, values)
    comprehension_time = measure(normalize_comprehension, values)

    print(f"Loop median:          {loop_time:.6f}s")
    print(f"Comprehension median: {comprehension_time:.6f}s")


if __name__ == "__main__":
    main()
