from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.taxonomy import CONCEPT_TYPES, DIFFICULTY_LABELS

_DIFFICULTY_DIRECTIONS = ("too_easy", "correct", "too_hard")


class FeedbackCreate(BaseModel):
    classification_is_correct: bool | None = None
    corrected_label: str | None = None
    difficulty_direction: str | None = None
    corrected_difficulty: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> FeedbackCreate:
        if self.corrected_label and self.corrected_label not in CONCEPT_TYPES:
            raise ValueError(f"corrected_label must be one of {CONCEPT_TYPES}")
        if self.corrected_difficulty and self.corrected_difficulty not in DIFFICULTY_LABELS:
            raise ValueError(f"corrected_difficulty must be one of {DIFFICULTY_LABELS}")
        if self.difficulty_direction and self.difficulty_direction not in _DIFFICULTY_DIRECTIONS:
            raise ValueError(f"difficulty_direction must be one of {_DIFFICULTY_DIRECTIONS}")
        if all(
            v is None
            for v in (
                self.classification_is_correct,
                self.corrected_label,
                self.difficulty_direction,
                self.corrected_difficulty,
                self.note,
            )
        ):
            raise ValueError("Feedback payload is empty.")
        return self


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    concept_id: int
    predicted_label: str | None = None
    corrected_label: str | None = None
    classification_is_correct: bool | None = None
    predicted_difficulty: str | None = None
    corrected_difficulty: str | None = None
    difficulty_direction: str | None = None
    note: str | None = None
    created_at: datetime
