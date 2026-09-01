"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

_ts = dict(server_default=sa.func.now(), nullable=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), **_ts),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_ts),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120)),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.false()),
        *_timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "lectures",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_name", sa.String(200), nullable=False),
        sa.Column("lecture_title", sa.String(300), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
        sa.Column("analysis_error", sa.Text),
        sa.Column("analyzed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_lectures_user_id", "lectures", ["user_id"])

    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("lecture_id", sa.Integer, sa.ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("extracted_text", sa.Text),
        sa.Column("page_count", sa.Integer),
        *_timestamps(),
    )
    op.create_index("ix_uploaded_files_lecture_id", "uploaded_files", ["lecture_id"])

    op.create_table(
        "text_chunks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("lecture_id", sa.Integer, sa.ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_id", sa.Integer, sa.ForeignKey("uploaded_files.id", ondelete="SET NULL")),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("char_count", sa.Integer, nullable=False),
        sa.Column("page_number", sa.Integer),
        sa.Column("slide_number", sa.Integer),
        sa.Column("paragraph_number", sa.Integer),
        sa.Column("section_title", sa.String(300)),
        *_timestamps(),
    )
    op.create_index("ix_text_chunks_lecture_id", "text_chunks", ["lecture_id"])

    op.create_table(
        "clusters",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("lecture_id", sa.Integer, sa.ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("algorithm", sa.String(40), nullable=False),
        sa.Column("cluster_index", sa.Integer, nullable=False),
        sa.Column("concept_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_difficulty_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("importance_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("keywords", sa.JSON),
        sa.Column("centroid_2d", sa.JSON),
        *_timestamps(),
    )
    op.create_index("ix_clusters_lecture_id", "clusters", ["lecture_id"])

    op.create_table(
        "concepts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("lecture_id", sa.Integer, sa.ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", sa.Integer, sa.ForeignKey("text_chunks.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("snippet", sa.Text, nullable=False),
        sa.Column("source_page", sa.Integer),
        sa.Column("source_section", sa.String(300)),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("relevance_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("concept_type", sa.String(40)),
        sa.Column("concept_type_confidence", sa.Float),
        sa.Column("difficulty_label", sa.String(10)),
        sa.Column("difficulty_score", sa.Float),
        sa.Column("difficulty_confidence", sa.Float),
        sa.Column("embedding", sa.JSON),
        *_timestamps(),
    )
    op.create_index("ix_concepts_lecture_id", "concepts", ["lecture_id"])
    op.create_index("ix_concepts_name", "concepts", ["name"])

    op.create_table(
        "concept_cluster_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("concept_id", sa.Integer, sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cluster_id", sa.Integer, sa.ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("membership_score", sa.Float, nullable=False, server_default="1"),
        sa.Column("is_representative", sa.Boolean, nullable=False, server_default=sa.false()),
        *_timestamps(),
        sa.UniqueConstraint("concept_id", "cluster_id", name="uq_concept_cluster"),
    )
    op.create_index("ix_concept_cluster_links_concept_id", "concept_cluster_links", ["concept_id"])
    op.create_index("ix_concept_cluster_links_cluster_id", "concept_cluster_links", ["cluster_id"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("family", sa.String(40), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True)),
        sa.Column("metrics", sa.JSON),
        sa.Column("artifact_path", sa.String(1000)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.false()),
        *_timestamps(),
        sa.UniqueConstraint("name", "version", name="uq_model_name_version"),
    )
    op.create_index("ix_model_versions_name", "model_versions", ["name"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("concept_id", sa.Integer, sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_version_id", sa.Integer, sa.ForeignKey("model_versions.id", ondelete="SET NULL")),
        sa.Column("task", sa.String(40), nullable=False),
        sa.Column("predicted_label", sa.String(40), nullable=False),
        sa.Column("predicted_score", sa.Float),
        sa.Column("confidence", sa.Float),
        sa.Column("model_name", sa.String(80), nullable=False),
        sa.Column("model_version", sa.String(40), nullable=False),
        sa.Column("latency_ms", sa.Float),
        *_timestamps(),
    )
    op.create_index("ix_predictions_concept_id", "predictions", ["concept_id"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("concept_id", sa.Integer, sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("predicted_label", sa.String(40)),
        sa.Column("corrected_label", sa.String(40)),
        sa.Column("classification_is_correct", sa.Boolean),
        sa.Column("predicted_difficulty", sa.String(10)),
        sa.Column("corrected_difficulty", sa.String(10)),
        sa.Column("difficulty_direction", sa.String(20)),
        sa.Column("note", sa.Text),
        sa.Column("submitted_by", sa.String(320)),
        *_timestamps(),
    )
    op.create_index("ix_feedback_concept_id", "feedback", ["concept_id"])


def downgrade() -> None:
    for table in (
        "feedback",
        "predictions",
        "model_versions",
        "concept_cluster_links",
        "concepts",
        "clusters",
        "text_chunks",
        "uploaded_files",
        "lectures",
        "users",
    ):
        op.drop_table(table)
