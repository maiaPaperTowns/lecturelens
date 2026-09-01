"""End-to-end analysis pipeline orchestrator.

    files -> extract -> clean -> chunk -> concept extraction -> embeddings
          -> concept-type classification -> difficulty estimation -> clustering
          -> persistence

Every step is a thin call into ``app.ml.*``; this module only coordinates and
persists. Kept out of the API routes on purpose.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import AnalysisError
from app.core.logging import get_logger
from app.core.taxonomy import DIFFICULTY_TO_SCORE
from app.db.models import (
    Cluster,
    Concept,
    ConceptClusterLink,
    Feedback,
    Lecture,
    ModelVersion,
    Prediction,
    TextChunk,
    UploadedFile,
)
from app.ml.classification.concept_extractor import ConceptExtractor
from app.ml.clustering import choose_k, get_clusterer, label_cluster
from app.ml.difficulty.features import DifficultyContext
from app.ml.preprocessing import chunk_document, extract_document
from app.ml.registry import get_registry
from app.services.uploads import get_lecture, touch

logger = get_logger(__name__)

MIN_CHUNKS_FOR_ANALYSIS = 2
MIN_CONCEPTS_FOR_CLUSTERING = 4


@dataclass
class AnalysisResult:
    lecture_id: int
    status: str
    concept_count: int
    cluster_count: int
    chunk_count: int
    duration_ms: float
    model_versions: dict[str, str]
    warnings: list[str]


def _clear_previous(db: Session, lecture_id: int) -> None:
    """Remove all derived rows for a lecture so re-analysis is idempotent.

    Done explicitly (rather than relying on FK cascade) because SQLite does not
    enforce ``ON DELETE CASCADE`` by default and bulk deletes bypass ORM cascades.
    """
    concept_ids = [
        cid for (cid,) in db.execute(
            select(Concept.id).where(Concept.lecture_id == lecture_id)
        ).all()
    ]
    if concept_ids:
        db.execute(
            delete(ConceptClusterLink).where(ConceptClusterLink.concept_id.in_(concept_ids))
        )
        db.execute(delete(Prediction).where(Prediction.concept_id.in_(concept_ids)))
        db.execute(delete(Feedback).where(Feedback.concept_id.in_(concept_ids)))
    db.execute(delete(Concept).where(Concept.lecture_id == lecture_id))
    db.execute(delete(Cluster).where(Cluster.lecture_id == lecture_id))
    db.execute(delete(TextChunk).where(TextChunk.lecture_id == lecture_id))
    db.flush()


def _upsert_model_version(db: Session, name: str, family: str, version: str) -> ModelVersion:
    mv = db.execute(
        select(ModelVersion).where(ModelVersion.name == name, ModelVersion.version == version)
    ).scalar_one_or_none()
    if mv is None:
        mv = ModelVersion(name=name, family=family, version=version, is_active=True)
        db.add(mv)
        db.flush()
    return mv


def analyze_lecture(db: Session, lecture_id: int) -> AnalysisResult:
    lecture = get_lecture(db, lecture_id)
    started = time.perf_counter()
    warnings: list[str] = []
    touch(lecture, "processing")
    db.flush()

    try:
        chunks = _build_chunks(db, lecture)
        if len(chunks) < MIN_CHUNKS_FOR_ANALYSIS:
            raise AnalysisError("Not enough usable text to analyse this lecture.")

        registry = get_registry()
        embedder = registry.get_embedder(corpus_fallback=[c.text for c in chunks])

        concepts = _extract_concepts(db, lecture, chunks, embedder)
        if not concepts:
            raise AnalysisError("No concepts could be detected in this lecture.")

        model_versions = _classify_concepts(db, concepts, registry)
        model_versions.update(_estimate_difficulty(db, lecture, concepts, registry))

        cluster_count = _cluster_concepts(db, lecture, concepts, warnings)

        touch(lecture, "analyzed")
        db.flush()
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        logger.info(
            "Analysed lecture %s: %d concepts, %d clusters, %.0fms",
            lecture_id, len(concepts), cluster_count, duration_ms,
        )
        return AnalysisResult(
            lecture_id=lecture_id,
            status="analyzed",
            concept_count=len(concepts),
            cluster_count=cluster_count,
            chunk_count=len(chunks),
            duration_ms=duration_ms,
            model_versions=model_versions,
            warnings=warnings,
        )
    except AnalysisError as exc:
        touch(lecture, "failed", str(exc))
        db.flush()
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Analysis crashed for lecture %s", lecture_id)
        touch(lecture, "failed", f"Unexpected error: {exc}")
        db.flush()
        raise AnalysisError("Analysis failed unexpectedly. See server logs.") from exc


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------
def _build_chunks(db: Session, lecture: Lecture) -> list[TextChunk]:
    _clear_previous(db, lecture.id)
    files = db.execute(
        select(UploadedFile).where(UploadedFile.lecture_id == lecture.id)
    ).scalars().all()

    rows: list[TextChunk] = []
    order = 0
    for file in files:
        try:
            document = extract_document(file.storage_path, file_name=file.file_name)
        except Exception as exc:
            logger.warning("Re-extraction failed for file %s: %s", file.id, exc)
            continue
        for chunk in chunk_document(document):
            order += 1
            rows.append(
                TextChunk(
                    lecture_id=lecture.id,
                    file_id=file.id,
                    order_index=order,
                    text=chunk.text,
                    char_count=chunk.char_count,
                    page_number=chunk.page_number,
                    slide_number=chunk.slide_number,
                    paragraph_number=chunk.paragraph_number,
                    section_title=chunk.section_title,
                )
            )
    db.add_all(rows)
    db.flush()
    return rows


def _extract_concepts(
    db: Session, lecture: Lecture, chunks: list[TextChunk], embedder
) -> list[Concept]:
    from app.ml.preprocessing.chunk import Chunk as ChunkDTO

    dtos = [
        ChunkDTO(
            order_index=c.order_index,
            text=c.text,
            char_count=c.char_count,
            page_number=c.page_number,
            slide_number=c.slide_number,
            paragraph_number=c.paragraph_number,
            section_title=c.section_title,
        )
        for c in chunks
    ]
    candidates = ConceptExtractor(max_concepts=40).extract(dtos)
    if not candidates:
        return []

    embed_inputs = [f"{c.name}. {c.snippet}" for c in candidates]
    embeddings = embedder.transform(embed_inputs)

    concepts: list[Concept] = []
    for idx, cand in enumerate(candidates):
        concept = Concept(
            lecture_id=lecture.id,
            chunk_id=chunks[cand.chunk_index].id,
            name=cand.name[:300],
            snippet=cand.snippet,
            source_page=cand.source_page,
            source_section=cand.source_section,
            order_index=idx,
            relevance_score=cand.relevance_score,
            embedding=[round(float(v), 5) for v in embeddings[idx]],
        )
        concepts.append(concept)
    db.add_all(concepts)
    db.flush()
    return concepts


def _classify_concepts(db: Session, concepts: list[Concept], registry) -> dict[str, str]:
    classifier = registry.get_concept_classifier()
    preds = classifier.predict([c.snippet for c in concepts])
    mv = _upsert_model_version(db, "concept_classifier", getattr(classifier, "family", "heuristic"),
                               preds[0].model_version if preds else "heuristic-v1")
    for concept, pred in zip(concepts, preds, strict=True):
        concept.concept_type = pred.label
        concept.concept_type_confidence = pred.confidence
        db.add(
            Prediction(
                concept_id=concept.id,
                model_version_id=mv.id,
                task="concept_type",
                predicted_label=pred.label,
                confidence=pred.confidence,
                model_name=pred.model_name,
                model_version=pred.model_version,
                latency_ms=pred.latency_ms,
            )
        )
    db.flush()
    return {"concept_classifier": preds[0].model_version if preds else "heuristic-v1"}


def _estimate_difficulty(
    db: Session, lecture: Lecture, concepts: list[Concept], registry
) -> dict[str, str]:
    classifier = registry.get_difficulty_classifier()
    lecture_text = " ".join(c.snippet for c in concepts).lower()
    ctx = DifficultyContext(
        all_concept_names=[c.name for c in concepts], lecture_text_lower=lecture_text
    )
    preds = classifier.predict(
        [c.name for c in concepts], [c.snippet for c in concepts], ctx
    )
    mv = _upsert_model_version(db, "difficulty", getattr(classifier, "family", "heuristic"),
                               preds[0].model_version if preds else "heuristic-v1")
    for concept, pred in zip(concepts, preds, strict=True):
        concept.difficulty_label = pred.label
        concept.difficulty_score = pred.score
        concept.difficulty_confidence = pred.confidence
        db.add(
            Prediction(
                concept_id=concept.id,
                model_version_id=mv.id,
                task="difficulty",
                predicted_label=pred.label,
                predicted_score=pred.score,
                confidence=pred.confidence,
                model_name=pred.model_name,
                model_version=pred.model_version,
                latency_ms=pred.latency_ms,
            )
        )
    db.flush()
    return {"difficulty": preds[0].model_version if preds else "heuristic-v1"}


def _cluster_concepts(
    db: Session, lecture: Lecture, concepts: list[Concept], warnings: list[str], algorithm: str = "kmeans"
) -> int:
    if len(concepts) < MIN_CONCEPTS_FOR_CLUSTERING:
        warnings.append("Too few concepts for clustering; created a single study cluster.")
        return _single_cluster(db, lecture, concepts, algorithm)

    X = np.array([c.embedding for c in concepts], dtype=np.float32)
    k = choose_k(X)
    labels = get_clusterer(algorithm, n_clusters=k).fit_predict(X)

    total_relevance = sum(c.relevance_score for c in concepts) or 1.0
    n_clusters = 0
    for cluster_idx in sorted(set(labels)):
        members = [c for c, lbl in zip(concepts, labels, strict=True) if lbl == cluster_idx]
        if not members:
            continue
        member_emb = np.array([c.embedding for c in members], dtype=np.float32)
        summary = label_cluster(
            [c.id for c in members],
            [c.name for c in members],
            [c.snippet for c in members],
            member_emb,
        )
        avg_diff = float(
            np.mean([c.difficulty_score or DIFFICULTY_TO_SCORE["medium"] for c in members])
        )
        importance = round(sum(c.relevance_score for c in members) / total_relevance, 4)
        cluster = Cluster(
            lecture_id=lecture.id,
            label=summary.label,
            algorithm=algorithm,
            cluster_index=int(cluster_idx),
            concept_count=len(members),
            avg_difficulty_score=round(avg_diff, 4),
            importance_score=importance,
            keywords=summary.keywords,
            centroid_2d=[float(v) for v in member_emb.mean(axis=0)[:2]],
        )
        db.add(cluster)
        db.flush()
        rep_ids = set(summary.representative_concept_ids)
        for concept in members:
            db.add(
                ConceptClusterLink(
                    concept_id=concept.id,
                    cluster_id=cluster.id,
                    membership_score=1.0,
                    is_representative=concept.id in rep_ids,
                )
            )
        n_clusters += 1
    db.flush()
    return n_clusters


def _single_cluster(db: Session, lecture: Lecture, concepts: list[Concept], algorithm: str) -> int:
    if not concepts:
        return 0
    member_emb = np.array([c.embedding for c in concepts], dtype=np.float32)
    summary = label_cluster(
        [c.id for c in concepts], [c.name for c in concepts], [c.snippet for c in concepts], member_emb
    )
    cluster = Cluster(
        lecture_id=lecture.id,
        label=summary.label or "All concepts",
        algorithm=algorithm,
        cluster_index=0,
        concept_count=len(concepts),
        avg_difficulty_score=round(
            float(np.mean([c.difficulty_score or 0.55 for c in concepts])), 4
        ),
        importance_score=1.0,
        keywords=summary.keywords,
        centroid_2d=[float(v) for v in member_emb.mean(axis=0)[:2]],
    )
    db.add(cluster)
    db.flush()
    for concept in concepts:
        db.add(ConceptClusterLink(concept_id=concept.id, cluster_id=cluster.id))
    db.flush()
    return 1


def related_concepts(concept: Concept, siblings: list[Concept], top_k: int = 5) -> list[dict]:
    """Cosine-similarity nearest neighbours within the same lecture."""
    others = [c for c in siblings if c.id != concept.id and c.embedding]
    if not concept.embedding or not others:
        return []
    base = np.array(concept.embedding, dtype=np.float32).reshape(1, -1)
    mat = np.array([c.embedding for c in others], dtype=np.float32)
    sims = cosine_similarity(base, mat)[0]
    ranked = np.argsort(sims)[::-1][:top_k]
    return [
        {
            "id": others[i].id,
            "name": others[i].name,
            "concept_type": others[i].concept_type,
            "difficulty_label": others[i].difficulty_label,
            "similarity": round(float(sims[i]), 4),
        }
        for i in ranked
        if sims[i] > 0.05
    ]
