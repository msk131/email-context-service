"""Prometheus metrics routes."""
from fastapi import APIRouter
from fastapi.responses import Response

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
except ImportError:
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    def generate_latest() -> bytes:
        return b""

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint for local development."""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
