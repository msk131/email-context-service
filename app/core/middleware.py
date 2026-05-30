"""HTTP middleware components."""

from fastapi import FastAPI, Request
from fastapi.responses import Response

from app.core.logging_config import configure_logging, request_id_ctx_var
from app.core.request_handlers import (
    add_request_id_to_response,
    extract_or_generate_request_id,
)

logger = configure_logging()


def setup_middleware(app: FastAPI) -> None:
    """Register all HTTP middleware."""

    @app.middleware("http")
    async def append_request_id_middleware(request: Request, call_next):
        """
        Middleware to capture or generate request ID for every HTTP request.

        Production-grade behavior:
        - Reads X-Request-ID header if provided by client (for tracing across services)
        - Generates new UUID4 if not provided
        - Stores in ContextVar for access across async calls
        - Returns request ID in X-Request-ID response header
        - Resets context after request completes (prevents context leakage in concurrent requests)
        """
        req_id = extract_or_generate_request_id(request)
        request.state.request_id = req_id

        # Save token into ContextVar so it's accessible across threads/async tasks
        token = request_id_ctx_var.set(req_id)

        logger.info(f"Incoming request: {request.method} {request.url.path}")

        try:
            response: Response = await call_next(request)
            # Return the Request ID in response headers
            add_request_id_to_response(response, req_id)
            return response
        finally:
            # Reset the context variable after the request finishes to avoid leakage in concurrent requests
            request_id_ctx_var.reset(token)
