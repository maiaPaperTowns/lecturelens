from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.concept import ConceptDetail
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.services.concepts import get_concept_detail
from app.services.feedback import create_feedback

router = APIRouter()


@router.get("/{concept_id}", response_model=ConceptDetail, summary="Concept detail view")
def concept_detail(concept_id: int, db: Session = Depends(get_db)) -> ConceptDetail:
    return ConceptDetail.model_validate(get_concept_detail(db, concept_id))


@router.post(
    "/{concept_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback on a concept's classification / difficulty",
)
def submit_feedback(
    concept_id: int, payload: FeedbackCreate, db: Session = Depends(get_db)
) -> FeedbackResponse:
    entry = create_feedback(db, concept_id, payload)
    return FeedbackResponse.model_validate(entry)
