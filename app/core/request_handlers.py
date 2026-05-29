"""Request handling utilities for middleware and request context management."""
import uuid
from contextvars import ContextVar
from fastapi import Request
from fastapi.responses import Response

# This should be imported from logging_config where it's actually defined
# For now, we'll reference it here
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default=None)


def extract_or_generate_request_id(request: Request) -> str:
    """
    Extract request ID from headers or generate a new one.
    
    Production-grade behavior:
    - Reads X-Request-ID header if provided by client (for tracing across services)
    - Generates new UUID4 if not provided
    - Handles empty/whitespace-only headers gracefully
    """
    req_id = request.headers.get("X-Request-ID")
    if not req_id or not req_id.strip():
        req_id = str(uuid.uuid4())
    else:
        req_id = req_id.strip()
    return req_id


def get_request_id(request: Request) -> str:
    """
    Retrieve request ID from multiple sources in priority order.
    
    Sources (in priority):
    1. request.state.request_id (set by middleware)
    2. X-Request-ID header
    3. ContextVar (from context)
    4. Generate new UUID
    """
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return request_id
    
    header_request_id = request.headers.get("X-Request-ID")
    if header_request_id and header_request_id.strip():
        return header_request_id.strip()
    
    context_request_id = request_id_ctx_var.get()
    if context_request_id:
        return context_request_id
    
    return str(uuid.uuid4())


def add_request_id_to_response(response: Response, request_id: str) -> None:
    """Add request ID to response headers."""
    response.headers["X-Request-ID"] = request_id
