"""FastAPI app configuration and exception handlers setup."""
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.common.error_handlers import (
    generic_error_response,
    http_exception_response,
    validation_error_response,
)
from app.common.rate_limit import RateLimitExceeded, limiter, rate_limit_exception_handler
from app.core.request_handlers import get_request_id

# API documentation metadata
TAGS_METADATA = [
    {"name": "health", "description": "Application health and readiness checks."},
    {"name": "clients", "description": "Client metadata lookup with firm-scoped authorization."},
    {"name": "emails", "description": "Client email retrieval and context operations."},
    {"name": "firms", "description": "Firm metadata and organization information."},
    {"name": "summaries", "description": "Summary generation, email search, conversational Q&A, and coverage reporting."},
    {"name": "setup", "description": "Bootstrap user registration, authentication, and demo data generation."},
    {"name": "tasks", "description": "Background task submission and status monitoring."},
]


def create_app(app_name: str, version: str = "1.0.0", lifespan=None) -> FastAPI:
    """
    Create and configure FastAPI application instance.
    
    Args:
        app_name: Application name for OpenAPI documentation
        version: Application version
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=app_name,
        version=version,
        lifespan=lifespan,
        description=(
            "Email Context & Summarization API for accounting teams. The system captures "
            "firm-client email interactions, generates client summaries, enables secure "
            "search and conversational Q&A, and delivers firm-scoped reporting."
        ),
        openapi_tags=TAGS_METADATA,
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
    
    return app


def setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with error ID and standardized error code."""
        error_id = get_request_id(request)
        return http_exception_response(request, exc, error_id)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors with detailed field information."""
        error_id = get_request_id(request)
        return validation_error_response(request, exc, error_id)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Global exception handler to capture unhandled errors and return the error ID.
        
        Production-grade behavior:
        - Logs full exception stack trace alongside the associated error ID
        - Returns opaque error_id to client (never exposes raw error details)
        - Developers can instantly find exact failure by searching error_id in logs
        """
        error_id = get_request_id(request)
        return generic_error_response(error_id, exc)


def setup_middleware_and_static(app: FastAPI) -> None:
    """Configure rate limiting and static files."""
    # Apply rate limiter to app
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
