from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.upload import AnalyzeResponse
from app.services.analysis import analyze_lecture

router = APIRouter()


@router.post(
    "/{upload_id}",
    response_model=AnalyzeResponse,
    summary="Run the ML analysis pipeline for an upload",
)
def run_analysis(upload_id: int, db: Session = Depends(get_db)) -> AnalyzeResponse:
    result = analyze_lecture(db, upload_id)
    return AnalyzeResponse(
        lecture_id=result.lecture_id,
        status=result.status,
        concept_count=result.concept_count,
        cluster_count=result.cluster_count,
        chunk_count=result.chunk_count,
        duration_ms=result.duration_ms,
        model_versions=result.model_versions,
        warnings=result.warnings,
    )
