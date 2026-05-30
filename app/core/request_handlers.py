"""Request handling utilities for middleware and request context management."""

import re
import uuid
from fastapi import Request
from fastapi.responses import Response

from app.core.logging_config import request_id_ctx_var
from app.core.setting import settings

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


def _is_valid_request_id(value: str) -> bool:
    """Accept only log-safe, bounded request IDs."""
    return (
        bool(value)
        and value != "-"
        and len(value) <= settings.request_id_max_length
        and _REQUEST_ID_RE.fullmatch(value) is not None
    )


def extract_or_generate_request_id(request: Request) -> str:
    """
    Extract request ID from headers or generate a new one.

    Production-grade behavior:
    - Reads X-Request-ID header if provided by client (for tracing across services)
    - Generates new UUID4 if not provided
    - Handles empty/whitespace-only headers gracefully
    """
    req_id = (request.headers.get("X-Request-ID") or "").strip()
    if not _is_valid_request_id(req_id):
        return str(uuid.uuid4())
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

    header_request_id = (request.headers.get("X-Request-ID") or "").strip()
    if _is_valid_request_id(header_request_id):
        return header_request_id

    context_request_id = request_id_ctx_var.get()
    if _is_valid_request_id(context_request_id):
        return context_request_id

    return str(uuid.uuid4())


def add_request_id_to_response(response: Response, request_id: str) -> None:
    """Add request ID to response headers."""
    response.headers["X-Request-ID"] = request_id
