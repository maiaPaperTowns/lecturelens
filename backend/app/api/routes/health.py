from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.db.session import get_db
from app.ml.registry import get_registry
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Service + dependency health")
def health(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:  # pragma: no cover - depends on infra
        db_status = f"error: {exc}"

    registry = get_registry()
    models = {}
    try:
        models["concept_classifier"] = getattr(
            registry.get_concept_classifier(), "version", "unknown"
        )
        models["difficulty"] = getattr(registry.get_difficulty_classifier(), "version", "unknown")
    except Exception as exc:  # pragma: no cover
        models["error"] = str(exc)

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        version=__version__,
        database=db_status,
        models=models,
    )
