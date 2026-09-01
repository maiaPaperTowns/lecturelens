from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.concept import ConceptSummary


class ClusterConceptPoint(BaseModel):
    id: int
    name: str
    difficulty_label: str | None = None
    difficulty_score: float | None = None
    concept_type: str | None = None
    x: float
    y: float
    is_representative: bool = False


class ClusterDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    algorithm: str
    cluster_index: int
    concept_count: int
    avg_difficulty_score: float
    importance_score: float
    keywords: list[str] = Field(default_factory=list)
    difficulty_distribution: dict[str, int] = Field(default_factory=dict)
    concepts: list[ConceptSummary] = Field(default_factory=list)
    points: list[ClusterConceptPoint] = Field(default_factory=list)


class ClusterListResponse(BaseModel):
    lecture_id: int
    algorithm: str
    total: int
    clusters: list[ClusterDetail]
