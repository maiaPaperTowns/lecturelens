from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.metrics import ModelMetricsResponse
from app.services.metrics import model_metrics

router = APIRouter()


@router.get("/metrics", response_model=ModelMetricsResponse, summary="Model + feedback metrics")
def metrics(db: Session = Depends(get_db)) -> ModelMetricsResponse:
    return ModelMetricsResponse.model_validate(model_metrics(db))
