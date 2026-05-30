"""Error handling with request ID and error codes."""

from enum import Enum
from typing import Optional


class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""

    # Client errors (4xx)
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNPROCESSABLE_ENTITY = "UNPROCESSABLE_ENTITY"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Domain-specific errors
    CLIENT_NOT_FOUND = "CLIENT_NOT_FOUND"
    ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
    EMAIL_CAPTURE_FAILED = "EMAIL_CAPTURE_FAILED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"


class ErrorResponse:
    """Standardized error response builder."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int,
        request_id: str = "",
        details: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.details = details or {}

    def to_dict(self) -> dict:
        """Convert to response dictionary."""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "request_id": self.request_id,
                "details": self.details if self.details else None,
            }
        }


# Predefined error responses (best practices)
ERROR_CLIENT_NOT_FOUND = {
    "code": ErrorCode.CLIENT_NOT_FOUND,
    "status_code": 404,
    "message": "Client not found. Please ensure the client exists before capturing emails.",
}

ERROR_ACCOUNT_NOT_FOUND = {
    "code": ErrorCode.ACCOUNT_NOT_FOUND,
    "status_code": 404,
    "message": "Account not found. Please check the email address and try again.",
}

ERROR_EMAIL_CAPTURE_FAILED = {
    "code": ErrorCode.EMAIL_CAPTURE_FAILED,
    "status_code": 400,
    "message": "Email capture failed. Unable to process the email payload.",
}

ERROR_INVALID_CREDENTIALS = {
    "code": ErrorCode.INVALID_CREDENTIALS,
    "status_code": 401,
    "message": "Invalid email or password. Please check your credentials.",
}

ERROR_INSUFFICIENT_PERMISSIONS = {
    "code": ErrorCode.INSUFFICIENT_PERMISSIONS,
    "status_code": 403,
    "message": "You don't have permission to access this resource.",
}

ERROR_VALIDATION_FAILED = {
    "code": ErrorCode.VALIDATION_ERROR,
    "status_code": 422,
    "message": "Request validation failed. Please check the payload format.",
}

ERROR_INTERNAL = {
    "code": ErrorCode.INTERNAL_ERROR,
    "status_code": 500,
    "message": "An unexpected error occurred. Please contact support with the request ID.",
}
