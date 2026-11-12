"""Compare an SQLite query plan before and after adding an index."""

from __future__ import annotations

import sqlite3
from statistics import median
from timeit import repeat


ROW_COUNT = 50_000
TARGET_EMAIL = "user-42000@example.test"


def query_plan(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = ?",
        (TARGET_EMAIL,),
    ).fetchone()
    assert row is not None
    return str(row[3])


def query_users(connection: sqlite3.Connection) -> list[tuple[int, str]]:
    return connection.execute(
        "SELECT id, email FROM users WHERE email = ?",
        (TARGET_EMAIL,),
    ).fetchall()


def median_query_time(connection: sqlite3.Connection) -> float:
    return median(repeat(lambda: query_users(connection), number=20, repeat=7))


def demonstration() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)")
    connection.executemany(
        "INSERT INTO users (email) VALUES (?)",
        ((f"user-{number}@example.test",) for number in range(ROW_COUNT)),
    )

    before_plan = query_plan(connection)
    before_time = median_query_time(connection)

    connection.execute("CREATE INDEX users_email_idx ON users (email)")
    after_plan = query_plan(connection)
    after_time = median_query_time(connection)

    assert query_users(connection) == [(42_001, TARGET_EMAIL)]
    assert "SCAN" in before_plan
    assert "INDEX" in after_plan

    print(f"Before: {before_plan} ({before_time:.6f}s)")
    print(f"After:  {after_plan} ({after_time:.6f}s)")


if __name__ == "__main__":
    demonstration()
