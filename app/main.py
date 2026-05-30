"""Application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health, metrics
from app.api.v1 import auth, clients, emails, firms, mock_emails, summaries, tasks
from app.core.app_config import (
    create_app,
    setup_exception_handlers,
    setup_middleware_and_static,
)
from app.core.logging_config import configure_logging
from app.core.middleware import setup_middleware
from app.core.setting import settings
from app.db.database import engine

logger = configure_logging()


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("Starting up application...")
    logger.info("Application startup complete")
    yield
    logger.info("Shutting down application...")
    await engine.dispose()
    logger.info("Application shutdown complete")


app = create_app(settings.app_name, lifespan=lifespan)
setup_middleware_and_static(app)
setup_middleware(app)
setup_exception_handlers(app)

# Register all v1 API routes
app.include_router(health.router, prefix="/api")
app.include_router(metrics.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(emails.router, prefix="/api/v1")
app.include_router(firms.router, prefix="/api/v1")
app.include_router(mock_emails.router, prefix="/api/v1")
app.include_router(summaries.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
