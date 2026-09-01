"""Export collected user feedback into a supervised training dataset.

Each corrected concept becomes a labelled row that could be appended to
``data/training/*.jsonl`` for a future retraining run. Retraining is *not*
performed automatically in production; this script only prepares the data.

Run::

    python scripts/export_feedback.py --out data/training/feedback_export.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # allow `python scripts/x.py`

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.models import Concept, Feedback
from app.db.session import SessionLocal

logger = get_logger("export-feedback")


def build_rows(db) -> dict[str, list[dict]]:
    concept_rows: list[dict] = []
    difficulty_rows: list[dict] = []

    feedback = db.execute(select(Feedback).order_by(Feedback.created_at)).scalars().all()
    for entry in feedback:
        concept = db.get(Concept, entry.concept_id)
        if concept is None:
            continue

        if entry.corrected_label:
            concept_rows.append(
                {
                    "text": concept.snippet,
                    "label": entry.corrected_label,
                    "source": "feedback",
                    "concept_id": concept.id,
                }
            )
        elif entry.classification_is_correct and concept.concept_type:
            concept_rows.append(
                {
                    "text": concept.snippet,
                    "label": concept.concept_type,
                    "source": "feedback_confirmed",
                    "concept_id": concept.id,
                }
            )

        corrected_difficulty = entry.corrected_difficulty
        if not corrected_difficulty and entry.difficulty_direction in ("too_easy", "too_hard"):
            order = ["easy", "medium", "hard"]
            if concept.difficulty_label in order:
                idx = order.index(concept.difficulty_label)
                idx += -1 if entry.difficulty_direction == "too_hard" else 1
                corrected_difficulty = order[max(0, min(len(order) - 1, idx))]
        if corrected_difficulty:
            difficulty_rows.append(
                {
                    "name": concept.name,
                    "text": concept.snippet,
                    "label": corrected_difficulty,
                    "source": "feedback",
                    "concept_id": concept.id,
                }
            )

    return {"concept": concept_rows, "difficulty": difficulty_rows}


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/training/feedback_export.jsonl")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        rows = build_rows(db)
    finally:
        db.close()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined = [{"task": "concept_type", **r} for r in rows["concept"]] + [
        {"task": "difficulty", **r} for r in rows["difficulty"]
    ]
    out_path.write_text("\n".join(json.dumps(r) for r in combined) + ("\n" if combined else ""))
    logger.info(
        "Exported %d concept-type rows and %d difficulty rows -> %s",
        len(rows["concept"]), len(rows["difficulty"]), out_path,
    )


if __name__ == "__main__":
    main()
