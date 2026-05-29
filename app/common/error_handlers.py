"""Error handling utilities for consistent error responses and exception handling."""
from typing import Optional
from fastapi import status, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.error_codes import ErrorCode
from app.core.logging_config import configure_logging

logger = configure_logging()


def build_error_envelope(
    code: str,
    message: str,
    error_id: str,
    details: Optional[dict] = None,
) -> dict:
    """Build standardized error response envelope with error ID (request ID).
    
    Follows security best practices:
    - Never exposes raw stack traces or sensitive details
    - Uses opaque error_id so users can report issues
    - Developers can search backend logs by error_id to find exact failure
    
    Args:
        code: Error code (from ErrorCode enum or string)
        message: User-friendly error message
        error_id: Unique error/request ID for tracking
        details: Optional additional error details/context
    
    Returns:
        Dictionary with standardized error envelope structure
    """
    return {
        "error": {
            "code": code,
            "message": message,
            "error_id": error_id,
            "details": details
        }
    }


def http_exception_response(request: Request, exc: HTTPException, error_id: str) -> JSONResponse:
    """Build JSON response for HTTPException with error ID and standardized error code."""
    # Map status codes to error codes
    error_code_map = {
        400: ErrorCode.BAD_REQUEST.value,
        401: ErrorCode.UNAUTHORIZED.value,
        403: ErrorCode.FORBIDDEN.value,
        404: ErrorCode.NOT_FOUND.value,
        409: ErrorCode.CONFLICT.value,
        422: ErrorCode.VALIDATION_ERROR.value,
        429: ErrorCode.RATE_LIMIT_EXCEEDED.value,
        500: ErrorCode.INTERNAL_ERROR.value,
    }
    error_code = error_code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_envelope(error_code, str(exc.detail), error_id),
        headers={**(exc.headers or {}), "X-Request-ID": error_id},
    )


def validation_error_response(request: Request, exc: RequestValidationError, error_id: str) -> JSONResponse:
    """Build JSON response for validation errors with detailed field information."""
    errors = [{"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_error_envelope(
            ErrorCode.VALIDATION_ERROR.value,
            "Request validation failed. Please check the payload format.",
            error_id,
            {"errors": errors},
        ),
        headers={"X-Request-ID": error_id},
    )


def generic_error_response(error_id: str, exc: Optional[Exception] = None) -> JSONResponse:
    """Build JSON response for unhandled exceptions."""
    if exc:
        logger.error(f"Unhandled exception occurred: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_envelope(
            ErrorCode.INTERNAL_ERROR.value,
            "An unexpected error occurred. Please contact support with error ID for assistance.",
            error_id,
        ),
        headers={"X-Request-ID": error_id},
    )
