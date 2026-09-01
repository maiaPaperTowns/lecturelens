from __future__ import annotations

from pydantic import BaseModel, Field


class ModelCardOut(BaseModel):
    name: str
    family: str
    version: str
    trained_at: str | None = None
    is_active: bool
    metrics: dict = Field(default_factory=dict)


class FeedbackStats(BaseModel):
    total: int
    classification_flagged_incorrect: int
    difficulty_flagged_off: int
    corrections_with_label: int
    by_concept_type: dict[str, int] = Field(default_factory=dict)
    recent: list[dict] = Field(default_factory=list)


class PredictionStats(BaseModel):
    total_predictions: int
    by_task: dict[str, int] = Field(default_factory=dict)
    by_model_version: dict[str, int] = Field(default_factory=dict)
    avg_latency_ms: float | None = None
    p95_latency_ms: float | None = None


class ModelMetricsResponse(BaseModel):
    models: list[ModelCardOut]
    feedback: FeedbackStats
    predictions: PredictionStats
    lectures_analyzed: int
    concepts_total: int
    clusters_total: int
