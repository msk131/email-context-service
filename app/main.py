"""Application entry point with N-layer architecture.

The app follows a clean layered architecture:
  HTTP Layer (api/v1/) → Business Logic (services/) → Data Access (repositories/) → Database (models/)
  - api/v1/: HTTP routes and endpoints
  - services/: Business logic (authentication, authorization, summarization)
  - repositories/: Data access layer (database queries)
  - models/: ORM models (SQLAlchemy)
  - schemas/: Pydantic validation models
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import health
from app.api.v1 import clients, emails, firms, setup, summaries
from app.core.config import settings
from app.db.database import engine
from app.common.models import Base

tags_metadata = [
    {"name": "health", "description": "Health check and status endpoints."},
    {"name": "clients", "description": "Client lookup with firm-scoped authorization."},
    {"name": "emails", "description": "Stored client email reads."},
    {"name": "firms", "description": "Firm lookup and organization metadata."},
    {"name": "summaries", "description": "Email summaries, refreshes, search, conversation, and reports."},
    {"name": "setup", "description": "Bootstrap users, roles, and mock data generation for demos."},
]

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Email Context API for CPA teams. The system stores mock firm-client email "
        "threads, summarizes client discussions into resolved items and open action "
        "items, protects sensitive summaries at rest, and exposes firm-scoped search, "
        "conversation, refresh, and reporting workflows."
    ),
    openapi_tags=tags_metadata,

    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "docExpansion": "none",
        "defaultModelRendering": "example",
        "displayRequestDuration": True,
        "filter": False,
        "operationsSorter": "alpha",
        "syntaxHighlight": {"theme": "monokai"},
        "showExtensions": True,
        "showCommonExtensions": True,
        "customCssUrl": "/static/swagger-custom.css",
    },
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Register all v1 API routes
app.include_router(health.router, prefix="/api")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(emails.router, prefix="/api/v1")
app.include_router(firms.router, prefix="/api/v1")
app.include_router(summaries.router, prefix="/api/v1")
app.include_router(setup.router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database on startup."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
