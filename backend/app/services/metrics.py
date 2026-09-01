"""Aggregate ML/product metrics for the model-metrics dashboard."""
from __future__ import annotations

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Cluster,
    Concept,
    Feedback,
    Lecture,
    Prediction,
)
from app.ml.registry import get_registry


def _feedback_stats(db: Session) -> dict:
    entries = list(db.execute(select(Feedback).order_by(Feedback.created_at.desc())).scalars())
    by_type: dict[str, int] = {}
    for e in entries:
        key = e.predicted_label or "unknown"
        by_type[key] = by_type.get(key, 0) + 1
    return {
        "total": len(entries),
        "classification_flagged_incorrect": sum(
            1 for e in entries if e.classification_is_correct is False
        ),
        "difficulty_flagged_off": sum(
            1 for e in entries if e.difficulty_direction in ("too_easy", "too_hard")
        ),
        "corrections_with_label": sum(1 for e in entries if e.corrected_label),
        "by_concept_type": by_type,
        "recent": [
            {
                "concept_id": e.concept_id,
                "predicted_label": e.predicted_label,
                "corrected_label": e.corrected_label,
                "predicted_difficulty": e.predicted_difficulty,
                "corrected_difficulty": e.corrected_difficulty,
                "difficulty_direction": e.difficulty_direction,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries[:15]
        ],
    }


def _prediction_stats(db: Session) -> dict:
    preds = list(db.execute(select(Prediction)).scalars())
    by_task: dict[str, int] = {}
    by_version: dict[str, int] = {}
    latencies: list[float] = []
    for p in preds:
        by_task[p.task] = by_task.get(p.task, 0) + 1
        vkey = f"{p.model_name}:{p.model_version}"
        by_version[vkey] = by_version.get(vkey, 0) + 1
        if p.latency_ms is not None:
            latencies.append(p.latency_ms)
    arr = np.array(latencies) if latencies else None
    return {
        "total_predictions": len(preds),
        "by_task": by_task,
        "by_model_version": by_version,
        "avg_latency_ms": round(float(arr.mean()), 3) if arr is not None else None,
        "p95_latency_ms": round(float(np.percentile(arr, 95)), 3) if arr is not None else None,
    }


def model_metrics(db: Session) -> dict:
    registry = get_registry()
    cards = [
        {
            "name": c.name,
            "family": c.family,
            "version": c.version,
            "trained_at": c.trained_at,
            "is_active": c.is_active,
            "metrics": c.metrics,
        }
        for c in registry.list_model_cards()
    ]
    return {
        "models": cards,
        "feedback": _feedback_stats(db),
        "predictions": _prediction_stats(db),
        "lectures_analyzed": db.scalar(
            select(func.count(Lecture.id)).where(Lecture.status == "analyzed")
        )
        or 0,
        "concepts_total": db.scalar(select(func.count(Concept.id))) or 0,
        "clusters_total": db.scalar(select(func.count(Cluster.id))) or 0,
    }
