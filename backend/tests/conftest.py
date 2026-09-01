"""Shared pytest fixtures.

Uses an on-disk SQLite database and a throwaway models directory so the suite
runs with no Postgres and no pre-trained artifacts (the heuristic models are
exercised).
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="lecturelens-tests-"))
# Force an isolated sqlite DB + throwaway dirs. This MUST override any ambient
# DATABASE_URL — the schema teardown drops every table, so the suite must never
# be able to point at a real database.
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["MODELS_DIR"] = str(_TMP / "models")
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["APP_ENV"] = "test"
os.environ.setdefault("LOG_LEVEL", "WARNING")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def sample_markdown() -> bytes:
    return (
        b"# Sorting Algorithms\n\n"
        b"## Definition\n\n"
        b"Merge sort is defined as a divide-and-conquer algorithm that splits the list "
        b"in half, recursively sorts each half, and merges the sorted halves together.\n\n"
        b"## Complexity Rule\n\n"
        b"Theorem: merge sort runs in O(n log n) time in the worst case because the "
        b"recursion tree has logarithmic depth and each level does linear work.\n\n"
        b"## Worked Example\n\n"
        b"For example, sorting [5, 2, 4, 1] first splits into [5, 2] and [4, 1], which "
        b"become [2, 5] and [1, 4], and then merge into [1, 2, 4, 5].\n\n"
        b"## Implementation Detail\n\n"
        b"The merge step uses two pointers and a temporary buffer the size of the input; "
        b"careful index bookkeeping avoids off-by-one errors.\n\n"
        b"## Comparison\n\n"
        b"Unlike quicksort, merge sort has a guaranteed worst case but needs extra memory, "
        b"whereas quicksort sorts in place but can degrade to quadratic time.\n\n"
        b"## Background\n\n"
        b"Merge sort was proposed by John von Neumann in 1945 and remains a standard "
        b"example when introducing recurrence relations and the master theorem.\n"
    )
