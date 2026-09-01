"""Domain exceptions and FastAPI exception handlers."""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class LectureLensError(Exception):
    """Base class for expected, user-facing errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "lecturelens_error"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFoundError(LectureLensError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class InvalidFileError(LectureLensError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "invalid_file"


class AnalysisError(LectureLensError):
    status_code = status.HTTP_409_CONFLICT
    code = "analysis_failed"


class ModelInferenceError(LectureLensError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "model_inference_failed"


def _payload(code: str, message: str, detail: object | None = None) -> dict:
    body: dict = {"error": {"code": code, "message": message}}
    if detail is not None:
        body["error"]["detail"] = detail
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LectureLensError)
    async def _handle_domain(_: Request, exc: LectureLensError) -> JSONResponse:
        logger.warning("Domain error (%s): %s", exc.code, exc.message)
        return JSONResponse(status_code=exc.status_code, content=_payload(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_payload(
                "validation_error",
                "Request validation failed",
                jsonable_encoder(exc.errors(), custom_encoder={Exception: str}),
            ),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload("internal_error", "An unexpected error occurred"),
        )
