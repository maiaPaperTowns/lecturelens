"""Read-side services for study clusters, incl. 2-D projection for viz."""
from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.taxonomy import DIFFICULTY_LABELS
from app.db.models import Cluster, Concept, ConceptClusterLink, Lecture
from app.ml.projection import project_2d
from app.services.concepts import _to_summary


def list_clusters(db: Session, lecture_id: int) -> dict:
    if db.get(Lecture, lecture_id) is None:
        raise NotFoundError(f"Lecture {lecture_id} not found.")

    clusters = db.execute(
        select(Cluster).where(Cluster.lecture_id == lecture_id).order_by(Cluster.importance_score.desc())
    ).scalars().all()
    links = db.execute(
        select(ConceptClusterLink).join(Cluster).where(Cluster.lecture_id == lecture_id)
    ).scalars().all()
    concepts = {
        c.id: c
        for c in db.execute(select(Concept).where(Concept.lecture_id == lecture_id)).scalars().all()
    }

    # one global projection so cross-cluster distances are comparable
    ordered_ids = [cid for cid in concepts if concepts[cid].embedding]
    coords: dict[int, tuple[float, float]] = {}
    if ordered_ids:
        emb = np.array([concepts[cid].embedding for cid in ordered_ids], dtype=np.float32)
        xy = project_2d(emb)
        coords = {cid: (float(x), float(y)) for cid, (x, y) in zip(ordered_ids, xy, strict=True)}

    links_by_cluster: dict[int, list[ConceptClusterLink]] = {}
    for link in links:
        links_by_cluster.setdefault(link.cluster_id, []).append(link)

    algorithm = clusters[0].algorithm if clusters else "kmeans"
    payload = []
    for cluster in clusters:
        member_links = links_by_cluster.get(cluster.id, [])
        members = [concepts[link.concept_id] for link in member_links if link.concept_id in concepts]
        rep_ids = {link.concept_id for link in member_links if link.is_representative}

        distribution = dict.fromkeys(DIFFICULTY_LABELS, 0)
        for concept in members:
            if concept.difficulty_label in distribution:
                distribution[concept.difficulty_label] += 1

        points = [
            {
                "id": concept.id,
                "name": concept.name,
                "difficulty_label": concept.difficulty_label,
                "difficulty_score": concept.difficulty_score,
                "concept_type": concept.concept_type,
                "x": coords.get(concept.id, (0.0, 0.0))[0],
                "y": coords.get(concept.id, (0.0, 0.0))[1],
                "is_representative": concept.id in rep_ids,
            }
            for concept in members
        ]

        payload.append(
            {
                "id": cluster.id,
                "label": cluster.label,
                "algorithm": cluster.algorithm,
                "cluster_index": cluster.cluster_index,
                "concept_count": cluster.concept_count,
                "avg_difficulty_score": cluster.avg_difficulty_score,
                "importance_score": cluster.importance_score,
                "keywords": cluster.keywords or [],
                "difficulty_distribution": distribution,
                "concepts": [
                    _to_summary(c, cluster)
                    for c in sorted(members, key=lambda x: x.relevance_score, reverse=True)
                ],
                "points": points,
            }
        )

    return {
        "lecture_id": lecture_id,
        "algorithm": algorithm,
        "total": len(payload),
        "clusters": payload,
    }
