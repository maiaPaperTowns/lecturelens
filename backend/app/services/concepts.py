"""Read-side services for concepts."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models import Cluster, Concept, ConceptClusterLink, Lecture, TextChunk
from app.services.analysis import related_concepts

_SORT_FIELDS = {
    "difficulty": lambda c: (c.difficulty_score or 0.0),
    "confidence": lambda c: (c.concept_type_confidence or 0.0),
    "relevance": lambda c: c.relevance_score,
    "source": lambda c: c.order_index,
}


def _cluster_lookup(db: Session, lecture_id: int) -> dict[int, Cluster]:
    rows = db.execute(
        select(ConceptClusterLink.concept_id, Cluster)
        .join(Cluster, Cluster.id == ConceptClusterLink.cluster_id)
        .where(Cluster.lecture_id == lecture_id)
    ).all()
    return dict(rows)


def _to_summary(concept: Concept, cluster: Cluster | None) -> dict:
    return {
        "id": concept.id,
        "name": concept.name,
        "concept_type": concept.concept_type,
        "concept_type_confidence": concept.concept_type_confidence,
        "difficulty_label": concept.difficulty_label,
        "difficulty_score": concept.difficulty_score,
        "difficulty_confidence": concept.difficulty_confidence,
        "relevance_score": concept.relevance_score,
        "source_page": concept.source_page,
        "source_section": concept.source_section,
        "order_index": concept.order_index,
        "cluster_id": cluster.id if cluster else None,
        "cluster_label": cluster.label if cluster else None,
    }


def list_concepts(
    db: Session,
    lecture_id: int,
    *,
    difficulty: str | None = None,
    concept_type: str | None = None,
    cluster_id: int | None = None,
    sort_by: str = "source",
    descending: bool = False,
) -> dict:
    if db.get(Lecture, lecture_id) is None:
        raise NotFoundError(f"Lecture {lecture_id} not found.")
    concepts = db.execute(
        select(Concept).where(Concept.lecture_id == lecture_id)
    ).scalars().all()
    clusters = _cluster_lookup(db, lecture_id)

    filtered = []
    for concept in concepts:
        cluster = clusters.get(concept.id)
        if difficulty and concept.difficulty_label != difficulty:
            continue
        if concept_type and concept.concept_type != concept_type:
            continue
        if cluster_id and (cluster is None or cluster.id != cluster_id):
            continue
        filtered.append((concept, cluster))

    key = _SORT_FIELDS.get(sort_by, _SORT_FIELDS["source"])
    filtered.sort(key=lambda pair: key(pair[0]), reverse=descending)

    return {
        "lecture_id": lecture_id,
        "total": len(filtered),
        "concepts": [_to_summary(c, cl) for c, cl in filtered],
    }


def get_concept_detail(db: Session, concept_id: int) -> dict:
    concept = db.execute(
        select(Concept)
        .options(selectinload(Concept.predictions), selectinload(Concept.feedback_entries))
        .where(Concept.id == concept_id)
    ).scalar_one_or_none()
    if concept is None:
        raise NotFoundError(f"Concept {concept_id} not found.")

    clusters = _cluster_lookup(db, concept.lecture_id)
    cluster = clusters.get(concept.id)
    siblings = db.execute(
        select(Concept).where(Concept.lecture_id == concept.lecture_id)
    ).scalars().all()
    chunk = db.get(TextChunk, concept.chunk_id) if concept.chunk_id else None

    predictions = sorted(concept.predictions, key=lambda p: p.created_at, reverse=True)
    model_versions = {}
    for pred in predictions:
        model_versions.setdefault(pred.task, pred.model_version)

    summary = _to_summary(concept, cluster)
    summary.update(
        {
            "snippet": concept.snippet,
            "original_text": chunk.text if chunk else concept.snippet,
            "cluster_label": cluster.label if cluster else None,
            "model_versions": model_versions,
            "related_concepts": related_concepts(concept, siblings),
            "predictions": [
                {
                    "task": p.task,
                    "predicted_label": p.predicted_label,
                    "predicted_score": p.predicted_score,
                    "confidence": p.confidence,
                    "model_name": p.model_name,
                    "model_version": p.model_version,
                    "latency_ms": p.latency_ms,
                    "created_at": p.created_at,
                }
                for p in predictions
            ],
            "feedback_count": len(concept.feedback_entries),
        }
    )
    return summary
