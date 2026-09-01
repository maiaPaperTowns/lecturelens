"""Seed the database with demo lectures so the app works right after setup.

Idempotent: existing demo lectures (matched by title) are skipped. Runs the full
analysis pipeline on each lecture so concepts, clusters and predictions are
populated.

Run::

    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --reset      # delete demo lectures first
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # allow `python scripts/x.py`

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.base import Base
from app.db.models import Lecture, UploadedFile
from app.db.session import SessionLocal, engine
from app.ml.preprocessing import extract_document
from app.services.analysis import analyze_lecture
from app.services.users import get_or_create_user
from scripts._dataset import DEMO_DIR

logger = get_logger("seed")

DEMO_LECTURES = [
    ("CS 201 · Algorithms", "Binary Search and Divide-and-Conquer", "binary_search.md"),
    ("CS 340 · Operating Systems", "CPU Scheduling", "operating_systems_scheduling.md"),
    ("CS 289 · Machine Learning", "Gradient Descent and the Bias–Variance Tradeoff",
     "machine_learning_gradient_descent.md"),
]


def _ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)


def _seed_one(db, course: str, title: str, filename: str) -> None:
    exists = db.execute(
        select(Lecture).where(Lecture.lecture_title == title, Lecture.course_name == course)
    ).scalar_one_or_none()
    if exists:
        logger.info("Skipping '%s' (already seeded, id=%s)", title, exists.id)
        return

    source = DEMO_DIR / filename
    if not source.exists():
        logger.warning("Demo file missing: %s", source)
        return

    user = get_or_create_user(db)
    lecture = Lecture(user_id=user.id, course_name=course, lecture_title=title, status="uploaded")
    db.add(lecture)
    db.flush()

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    stored = settings.upload_dir / f"demo_{lecture.id}_{filename}"
    shutil.copyfile(source, stored)
    document = extract_document(stored, file_name=filename)

    db.add(
        UploadedFile(
            lecture_id=lecture.id,
            file_name=filename,
            content_type="text/markdown",
            file_type="md",
            size_bytes=source.stat().st_size,
            storage_path=str(stored),
            extracted_text=document.full_text,
            page_count=document.page_count,
        )
    )
    db.flush()

    result = analyze_lecture(db, lecture.id)
    db.commit()
    logger.info(
        "Seeded '%s' -> %d concepts, %d clusters", title, result.concept_count, result.cluster_count
    )


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Delete demo lectures first")
    args = parser.parse_args()

    _ensure_schema()
    db = SessionLocal()
    try:
        if args.reset:
            titles = [t for _, t, _ in DEMO_LECTURES]
            for lecture in db.execute(
                select(Lecture).where(Lecture.lecture_title.in_(titles))
            ).scalars():
                db.delete(lecture)
            db.commit()
            logger.info("Reset: removed existing demo lectures")

        for course, title, filename in DEMO_LECTURES:
            _seed_one(db, course, title, filename)
    finally:
        db.close()


if __name__ == "__main__":
    main()
