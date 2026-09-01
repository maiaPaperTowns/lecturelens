"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger.info("LectureLens API %s starting (env=%s)", __version__, settings.app_env)
    # Warm the model registry so the first request is not slow.
    try:
        from app.ml.registry import get_registry

        registry = get_registry()
        registry.get_concept_classifier()
        registry.get_difficulty_classifier()
    except Exception as exc:  # pragma: no cover - non-fatal
        logger.warning("Model warm-up skipped: %s", exc)
    yield
    logger.info("LectureLens API shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="LectureLens API",
        version=__version__,
        description=(
            "Turn lecture notes, PDFs and slide decks into a structured study map: "
            "concept detection, difficulty estimation, clustering and a feedback loop. "
            "Powered by an offline PyTorch + scikit-learn pipeline."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {"name": "LectureLens API", "version": __version__, "docs": "/docs"}

    return app


app = create_app()
