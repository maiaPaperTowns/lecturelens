from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidFileError
from app.db.session import get_db
from app.schemas.upload import LectureDetail, LectureSummary, UploadResponse
from app.services import uploads as upload_service
from app.services.uploads import IncomingFile

router = APIRouter()


@router.post("", response_model=UploadResponse, status_code=201, summary="Upload lecture material")
async def create_upload(
    course_name: str = Form(..., min_length=1, max_length=200),
    lecture_title: str = Form(..., min_length=1, max_length=300),
    files: list[UploadFile] = File(..., description="PDF, TXT or Markdown files"),
    db: Session = Depends(get_db),
) -> UploadResponse:
    incoming: list[IncomingFile] = []
    for upload in files:
        data = await upload.read()
        incoming.append(
            IncomingFile(
                filename=upload.filename or "",
                content_type=upload.content_type or "",
                data=data,
            )
        )
    if not incoming:
        raise InvalidFileError("No files were provided.")

    lecture = upload_service.create_lecture(
        db, course_name=course_name, lecture_title=lecture_title, files=incoming
    )
    detail = upload_service.get_lecture_detail(db, lecture.id)
    return UploadResponse(lecture=LectureDetail.model_validate(detail))


@router.get("", response_model=list[LectureSummary], summary="List previous uploads")
def list_uploads(db: Session = Depends(get_db)) -> list[LectureSummary]:
    return [LectureSummary.model_validate(row) for row in upload_service.list_lectures(db)]


@router.get("/{upload_id}", response_model=LectureDetail, summary="Get one upload / lecture")
def get_upload(upload_id: int, db: Session = Depends(get_db)) -> LectureDetail:
    return LectureDetail.model_validate(upload_service.get_lecture_detail(db, upload_id))
