"""Canonical label sets shared by the ML pipeline, DB layer and API schemas."""
from __future__ import annotations

CONCEPT_TYPES: tuple[str, ...] = (
    "definition",
    "example",
    "theorem_or_rule",
    "process",
    "comparison",
    "implementation_detail",
    "background_information",
)

CONCEPT_TYPE_LABELS: dict[str, str] = {
    "definition": "Definition",
    "example": "Example",
    "theorem_or_rule": "Theorem / Rule",
    "process": "Process",
    "comparison": "Comparison",
    "implementation_detail": "Implementation Detail",
    "background_information": "Background",
}

DIFFICULTY_LABELS: tuple[str, ...] = ("easy", "medium", "hard")
DIFFICULTY_TO_SCORE: dict[str, float] = {"easy": 0.2, "medium": 0.55, "hard": 0.9}
SCORE_ORDER: dict[str, int] = {"easy": 0, "medium": 1, "hard": 2}


def score_to_difficulty(score: float) -> str:
    if score < 0.4:
        return "easy"
    if score < 0.7:
        return "medium"
    return "hard"
