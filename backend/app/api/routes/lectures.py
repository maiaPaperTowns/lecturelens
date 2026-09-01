from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.cluster import ClusterListResponse
from app.schemas.concept import ConceptListResponse
from app.services.clusters import list_clusters
from app.services.concepts import list_concepts

router = APIRouter()


@router.get(
    "/{lecture_id}/concepts",
    response_model=ConceptListResponse,
    summary="List concepts for a lecture (filter + sort)",
)
def get_concepts(
    lecture_id: int,
    difficulty: str | None = Query(None, pattern="^(easy|medium|hard)$"),
    concept_type: str | None = Query(None),
    cluster_id: int | None = Query(None),
    sort_by: str = Query("source", pattern="^(difficulty|confidence|relevance|source)$"),
    descending: bool = Query(False),
    db: Session = Depends(get_db),
) -> ConceptListResponse:
    data = list_concepts(
        db,
        lecture_id,
        difficulty=difficulty,
        concept_type=concept_type,
        cluster_id=cluster_id,
        sort_by=sort_by,
        descending=descending,
    )
    return ConceptListResponse.model_validate(data)


@router.get(
    "/{lecture_id}/clusters",
    response_model=ClusterListResponse,
    summary="List study clusters for a lecture (with 2-D projection)",
)
def get_clusters(lecture_id: int, db: Session = Depends(get_db)) -> ClusterListResponse:
    return ClusterListResponse.model_validate(list_clusters(db, lecture_id))
