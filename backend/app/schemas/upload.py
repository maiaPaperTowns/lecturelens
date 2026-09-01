from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

_CFG = ConfigDict(from_attributes=True, protected_namespaces=())


class UploadedFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    file_type: str
    size_bytes: int
    page_count: int | None = None
    created_at: datetime


class LectureSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_name: str
    lecture_title: str
    status: str
    created_at: datetime
    analyzed_at: datetime | None = None
    concept_count: int = 0
    cluster_count: int = 0


class LectureDetail(LectureSummary):
    analysis_error: str | None = None
    files: list[UploadedFileOut] = Field(default_factory=list)
    chunk_count: int = 0


class UploadResponse(BaseModel):
    lecture: LectureDetail
    message: str = "Upload received. Trigger analysis to build the study map."


class AnalyzeResponse(BaseModel):
    model_config = _CFG

    lecture_id: int
    status: str
    concept_count: int
    cluster_count: int
    chunk_count: int
    duration_ms: float
    model_versions: dict[str, str]
    warnings: list[str] = Field(default_factory=list)
