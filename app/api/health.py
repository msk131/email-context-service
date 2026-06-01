"""Health check routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.setting import settings
from app.db.database import get_session

router = APIRouter()


@router.get(
    "/health",
    tags=["health"],
    summary="Health check and service status",
    description="Returns a simple service health status for load balancers and uptime monitoring.",
    responses={200: {"description": "Service is healthy and responding."}},
)
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": settings.app_name}


@router.get(
    "/healthz",
    tags=["health"],
    summary="Dependency-aware health check",
    description="Validates that the API process and required database dependency are healthy.",
    responses={200: {"description": "Service dependencies are healthy."}},
)
async def healthz(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Dependency-aware health check for orchestrators."""
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name, "database": "ok"}
