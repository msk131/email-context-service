"""Health check routes."""

from fastapi import APIRouter

from app.core.setting import settings

router = APIRouter()


@router.get(
    "/health",
    tags=["health"],
    summary="Health check and service status",
    description="Returns a simple service health status for load balancers and uptime monitoring.",
    responses={200: {"description": "Service is healthy and responding."}},
)
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": settings.app_name}
