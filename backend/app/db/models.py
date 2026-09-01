"""ORM models for LectureLens.

Schema overview::

    users ──< lectures ──< uploaded_files ──< text_chunks
                 │                                  │
                 ├──< concepts >──┐            (chunk source)
                 │                │
                 ├──< clusters ──<┴ concept_cluster_links
                 │
    concepts ──< predictions
    concepts ──< feedback
    model_versions ──< predictions
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# ---------------------------------------------------------------------------
# Enumerated string values (kept as plain strings for portability + easy ML use)
# ---------------------------------------------------------------------------
CONCEPT_TYPES = (
    "definition",
    "example",
    "theorem_or_rule",
    "process",
    "comparison",
    "implementation_detail",
    "background_information",
)
DIFFICULTY_LABELS = ("easy", "medium", "hard")
UPLOAD_STATUSES = ("uploaded", "processing", "analyzed", "failed")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    lectures: Mapped[list[Lecture]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Lecture(Base, TimestampMixin):
    __tablename__ = "lectures"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_name: Mapped[str] = mapped_column(String(200))
    lecture_title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="uploaded", nullable=False)
    analysis_error: Mapped[str | None] = mapped_column(Text)
    analyzed_at: Mapped[datetime | None]

    user: Mapped[User] = relationship(back_populates="lectures")
    files: Mapped[list[UploadedFile]] = relationship(
        back_populates="lecture", cascade="all, delete-orphan"
    )
    chunks: Mapped[list[TextChunk]] = relationship(
        back_populates="lecture", cascade="all, delete-orphan"
    )
    concepts: Mapped[list[Concept]] = relationship(
        back_populates="lecture", cascade="all, delete-orphan"
    )
    clusters: Mapped[list[Cluster]] = relationship(
        back_populates="lecture", cascade="all, delete-orphan"
    )


class UploadedFile(Base, TimestampMixin):
    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    lecture_id: Mapped[int] = mapped_column(
        ForeignKey("lectures.id", ondelete="CASCADE"), index=True
    )
    file_name: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(120))
    file_type: Mapped[str] = mapped_column(String(20))  # pdf | txt | md
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(1000))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)

    lecture: Mapped[Lecture] = relationship(back_populates="files")


class TextChunk(Base, TimestampMixin):
    __tablename__ = "text_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    lecture_id: Mapped[int] = mapped_column(
        ForeignKey("lectures.id", ondelete="CASCADE"), index=True
    )
    file_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_files.id", ondelete="SET NULL"))
    order_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer)
    slide_number: Mapped[int | None] = mapped_column(Integer)
    paragraph_number: Mapped[int | None] = mapped_column(Integer)
    section_title: Mapped[str | None] = mapped_column(String(300))

    lecture: Mapped[Lecture] = relationship(back_populates="chunks")
    concepts: Mapped[list[Concept]] = relationship(back_populates="chunk")


class Concept(Base, TimestampMixin):
    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    lecture_id: Mapped[int] = mapped_column(
        ForeignKey("lectures.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("text_chunks.id", ondelete="SET NULL"))

    name: Mapped[str] = mapped_column(String(300), index=True)
    snippet: Mapped[str] = mapped_column(Text)
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_section: Mapped[str | None] = mapped_column(String(300))
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    # relevance of the concept within the lecture (TF-IDF / embedding based)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    # cached "current" predictions for fast reads (full history in `predictions`)
    concept_type: Mapped[str | None] = mapped_column(String(40))
    concept_type_confidence: Mapped[float | None] = mapped_column(Float)
    difficulty_label: Mapped[str | None] = mapped_column(String(10))
    difficulty_score: Mapped[float | None] = mapped_column(Float)
    difficulty_confidence: Mapped[float | None] = mapped_column(Float)

    embedding: Mapped[list[float] | None] = mapped_column(JSON)

    lecture: Mapped[Lecture] = relationship(back_populates="concepts")
    chunk: Mapped[TextChunk | None] = relationship(back_populates="concepts")
    cluster_links: Mapped[list[ConceptClusterLink]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )
    predictions: Mapped[list[Prediction]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )
    feedback_entries: Mapped[list[Feedback]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )


class Cluster(Base, TimestampMixin):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    lecture_id: Mapped[int] = mapped_column(
        ForeignKey("lectures.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(300))
    algorithm: Mapped[str] = mapped_column(String(40))
    cluster_index: Mapped[int] = mapped_column(Integer)
    concept_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_difficulty_score: Mapped[float] = mapped_column(Float, default=0.0)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)
    keywords: Mapped[list[str] | None] = mapped_column(JSON)
    centroid_2d: Mapped[list[float] | None] = mapped_column(JSON)

    lecture: Mapped[Lecture] = relationship(back_populates="clusters")
    concept_links: Mapped[list[ConceptClusterLink]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan"
    )


class ConceptClusterLink(Base, TimestampMixin):
    __tablename__ = "concept_cluster_links"
    __table_args__ = (UniqueConstraint("concept_id", "cluster_id", name="uq_concept_cluster"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.id", ondelete="CASCADE"), index=True)
    membership_score: Mapped[float] = mapped_column(Float, default=1.0)
    is_representative: Mapped[bool] = mapped_column(Boolean, default=False)

    concept: Mapped[Concept] = relationship(back_populates="cluster_links")
    cluster: Mapped[Cluster] = relationship(back_populates="concept_links")


class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_model_name_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), index=True)  # concept_classifier | difficulty
    family: Mapped[str] = mapped_column(String(40))  # sklearn | pytorch
    version: Mapped[str] = mapped_column(String(40))
    trained_at: Mapped[datetime | None]
    metrics: Mapped[dict | None] = mapped_column(JSON)
    artifact_path: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    predictions: Mapped[list[Prediction]] = relationship(back_populates="model_version_ref")


class Prediction(Base, TimestampMixin):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id", ondelete="SET NULL")
    )
    task: Mapped[str] = mapped_column(String(40))  # concept_type | difficulty
    predicted_label: Mapped[str] = mapped_column(String(40))
    predicted_score: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(80))
    model_version: Mapped[str] = mapped_column(String(40))
    latency_ms: Mapped[float | None] = mapped_column(Float)

    concept: Mapped[Concept] = relationship(back_populates="predictions")
    model_version_ref: Mapped[ModelVersion | None] = relationship(back_populates="predictions")


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)

    predicted_label: Mapped[str | None] = mapped_column(String(40))
    corrected_label: Mapped[str | None] = mapped_column(String(40))
    classification_is_correct: Mapped[bool | None] = mapped_column(Boolean)

    predicted_difficulty: Mapped[str | None] = mapped_column(String(10))
    corrected_difficulty: Mapped[str | None] = mapped_column(String(10))
    difficulty_direction: Mapped[str | None] = mapped_column(String(20))  # too_easy|correct|too_hard

    note: Mapped[str | None] = mapped_column(Text)
    submitted_by: Mapped[str | None] = mapped_column(String(320))

    concept: Mapped[Concept] = relationship(back_populates="feedback_entries")
