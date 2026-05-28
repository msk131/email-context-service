"""Health check routes."""
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": settings.app_name}
