"""Feedback capture + aggregation."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models import Concept, Feedback
from app.schemas.feedback import FeedbackCreate


def create_feedback(db: Session, concept_id: int, payload: FeedbackCreate) -> Feedback:
    concept = db.get(Concept, concept_id)
    if concept is None:
        raise NotFoundError(f"Concept {concept_id} not found.")

    entry = Feedback(
        concept_id=concept_id,
        predicted_label=concept.concept_type,
        corrected_label=payload.corrected_label,
        classification_is_correct=payload.classification_is_correct,
        predicted_difficulty=concept.difficulty_label,
        corrected_difficulty=payload.corrected_difficulty,
        difficulty_direction=payload.difficulty_direction,
        note=payload.note,
    )
    # An explicit correction implies the classification was wrong.
    if payload.corrected_label and payload.classification_is_correct is None:
        entry.classification_is_correct = payload.corrected_label == concept.concept_type
    db.add(entry)
    db.flush()
    return entry


def list_feedback_for_concept(db: Session, concept_id: int) -> list[Feedback]:
    return list(
        db.execute(
            select(Feedback).where(Feedback.concept_id == concept_id).order_by(Feedback.created_at.desc())
        ).scalars()
    )
