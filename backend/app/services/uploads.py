"""Upload handling: validation, storage, text extraction, persistence."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.exceptions import InvalidFileError, NotFoundError
from app.core.logging import get_logger
from app.db.models import Cluster, Concept, Lecture, TextChunk, UploadedFile
from app.ml.preprocessing import detect_file_type, extract_document
from app.services.users import get_or_create_user

logger = get_logger(__name__)


@dataclass
class IncomingFile:
    filename: str
    content_type: str
    data: bytes


def _validate(file: IncomingFile) -> str:
    if not file.filename:
        raise InvalidFileError("A file name is required.")
    file_type = detect_file_type(file.filename)  # raises InvalidFileError on bad extension
    if len(file.data) == 0:
        raise InvalidFileError(f"'{file.filename}' is empty.")
    if len(file.data) > settings.max_upload_bytes:
        raise InvalidFileError(
            f"'{file.filename}' is {len(file.data) / 1_048_576:.1f} MB; "
            f"limit is {settings.max_upload_mb} MB."
        )
    return file_type


def _store_file(data: bytes, original_name: str) -> Path:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    safe_suffix = Path(original_name).suffix.lower()
    path = settings.upload_dir / f"{uuid.uuid4().hex}{safe_suffix}"
    path.write_bytes(data)
    return path


def create_lecture(
    db: Session,
    *,
    course_name: str,
    lecture_title: str,
    files: list[IncomingFile],
) -> Lecture:
    if not files:
        raise InvalidFileError("At least one file is required.")
    if not course_name.strip() or not lecture_title.strip():
        raise InvalidFileError("course_name and lecture_title are required.")

    user = get_or_create_user(db)
    lecture = Lecture(
        user_id=user.id,
        course_name=course_name.strip(),
        lecture_title=lecture_title.strip(),
        status="uploaded",
    )
    db.add(lecture)
    db.flush()

    for incoming in files:
        file_type = _validate(incoming)
        stored_path = _store_file(incoming.data, incoming.filename)
        try:
            document = extract_document(stored_path, file_name=incoming.filename)
        except InvalidFileError:
            stored_path.unlink(missing_ok=True)
            raise
        db.add(
            UploadedFile(
                lecture_id=lecture.id,
                file_name=incoming.filename,
                content_type=incoming.content_type or "application/octet-stream",
                file_type=file_type,
                size_bytes=len(incoming.data),
                storage_path=str(stored_path),
                extracted_text=document.full_text,
                page_count=document.page_count,
            )
        )

    db.flush()
    logger.info("Created lecture %s with %d file(s)", lecture.id, len(files))
    return lecture


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------
def _counts(db: Session, lecture_ids: list[int]) -> dict[int, dict[str, int]]:
    if not lecture_ids:
        return {}
    concept_rows = db.execute(
        select(Concept.lecture_id, func.count(Concept.id))
        .where(Concept.lecture_id.in_(lecture_ids))
        .group_by(Concept.lecture_id)
    ).all()
    cluster_rows = db.execute(
        select(Cluster.lecture_id, func.count(Cluster.id))
        .where(Cluster.lecture_id.in_(lecture_ids))
        .group_by(Cluster.lecture_id)
    ).all()
    chunk_rows = db.execute(
        select(TextChunk.lecture_id, func.count(TextChunk.id))
        .where(TextChunk.lecture_id.in_(lecture_ids))
        .group_by(TextChunk.lecture_id)
    ).all()
    out: dict[int, dict[str, int]] = {lid: {"concepts": 0, "clusters": 0, "chunks": 0} for lid in lecture_ids}
    for lid, c in concept_rows:
        out[lid]["concepts"] = c
    for lid, c in cluster_rows:
        out[lid]["clusters"] = c
    for lid, c in chunk_rows:
        out[lid]["chunks"] = c
    return out


def list_lectures(db: Session) -> list[dict]:
    lectures = db.execute(select(Lecture).order_by(Lecture.created_at.desc())).scalars().all()
    counts = _counts(db, [lec.id for lec in lectures])
    result = []
    for lec in lectures:
        c = counts.get(lec.id, {})
        result.append(
            {
                "id": lec.id,
                "course_name": lec.course_name,
                "lecture_title": lec.lecture_title,
                "status": lec.status,
                "created_at": lec.created_at,
                "analyzed_at": lec.analyzed_at,
                "concept_count": c.get("concepts", 0),
                "cluster_count": c.get("clusters", 0),
            }
        )
    return result


def get_lecture(db: Session, lecture_id: int) -> Lecture:
    lecture = db.execute(
        select(Lecture).options(selectinload(Lecture.files)).where(Lecture.id == lecture_id)
    ).scalar_one_or_none()
    if lecture is None:
        raise NotFoundError(f"Lecture {lecture_id} not found.")
    return lecture


def get_lecture_detail(db: Session, lecture_id: int) -> dict:
    lecture = get_lecture(db, lecture_id)
    c = _counts(db, [lecture_id]).get(lecture_id, {})
    return {
        "id": lecture.id,
        "course_name": lecture.course_name,
        "lecture_title": lecture.lecture_title,
        "status": lecture.status,
        "analysis_error": lecture.analysis_error,
        "created_at": lecture.created_at,
        "analyzed_at": lecture.analyzed_at,
        "concept_count": c.get("concepts", 0),
        "cluster_count": c.get("clusters", 0),
        "chunk_count": c.get("chunks", 0),
        "files": lecture.files,
    }


def touch(lecture: Lecture, status: str, error: str | None = None) -> None:
    lecture.status = status
    lecture.analysis_error = error
    if status == "analyzed":
        lecture.analyzed_at = datetime.utcnow()
