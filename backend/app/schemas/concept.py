from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConceptSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    name: str
    concept_type: str | None = None
    concept_type_confidence: float | None = None
    difficulty_label: str | None = None
    difficulty_score: float | None = None
    difficulty_confidence: float | None = None
    relevance_score: float = 0.0
    source_page: int | None = None
    source_section: str | None = None
    order_index: int = 0
    cluster_id: int | None = None
    cluster_label: str | None = None


class RelatedConcept(BaseModel):
    id: int
    name: str
    concept_type: str | None = None
    difficulty_label: str | None = None
    similarity: float


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    task: str
    predicted_label: str
    predicted_score: float | None = None
    confidence: float | None = None
    model_name: str
    model_version: str
    latency_ms: float | None = None
    created_at: datetime


class ConceptDetail(ConceptSummary):
    snippet: str
    original_text: str | None = None
    cluster_label: str | None = None
    model_versions: dict[str, str] = Field(default_factory=dict)
    related_concepts: list[RelatedConcept] = Field(default_factory=list)
    predictions: list[PredictionOut] = Field(default_factory=list)
    feedback_count: int = 0


class ConceptListResponse(BaseModel):
    lecture_id: int
    total: int
    concepts: list[ConceptSummary]
