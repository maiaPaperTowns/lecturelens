from fastapi import APIRouter

from app.api.routes import analyze, concepts, health, lectures, models, uploads

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(analyze.router, prefix="/analyze", tags=["analysis"])
api_router.include_router(lectures.router, prefix="/lectures", tags=["lectures"])
api_router.include_router(concepts.router, prefix="/concepts", tags=["concepts"])
api_router.include_router(models.router, prefix="/models", tags=["models"])

__all__ = ["api_router"]
