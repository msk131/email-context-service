"""Rate limiting configuration and middleware for production readiness.

Strategies:
- Per-user: Based on authenticated user ID (for authenticated endpoints)
- Per-IP: Based on client IP address (for public endpoints)
- Global: Bucket across entire service

Uses slowapi library (fork of ratelimit with FastAPI support).
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from functools import wraps
from jose import JWTError, jwt

from app.common.error_codes import ErrorCode
from app.core.request_handlers import get_request_id
from app.core.setting import settings

try:
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
except ImportError:
    if settings.is_production:
        raise RuntimeError("slowapi must be installed when APP_ENV=production")

    class RateLimitExceeded(Exception):
        """Fallback exception used when slowapi is not installed."""

        detail = None

    def get_remote_address(request: Request) -> str:
        """Return a stable local fallback rate-limit key."""
        return request.client.host if request.client else "local"

    class Limiter:
        """No-op limiter fallback for test and minimal local environments."""

        def __init__(self, key_func):
            self.key_func = key_func

        def limit(self, _limit: str):
            def decorator(func):
                @wraps(func)
                async def wrapper(*args, **kwargs):
                    return await func(*args, **kwargs)

                return wrapper

            return decorator

def _auth_subject(request: Request) -> str | None:
    """Use the bearer token subject as a stable per-user key when present."""
    authorization = request.headers.get("Authorization") or ""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        claims = jwt.get_unverified_claims(token)
    except (JWTError, ValueError):
        return None
    subject = str(claims.get("sub") or "").strip()
    return subject[:128] if subject else None


def rate_limit_key(request: Request) -> str:
    """Prefer authenticated user identity; otherwise fall back to client IP."""
    subject = _auth_subject(request)
    if subject:
        return f"user:{subject}"
    return f"ip:{get_remote_address(request)}"


# Initialize rate limiter with a user-aware key instead of IP-only buckets.
limiter = Limiter(key_func=rate_limit_key)


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Handle rate limit exceeded errors with proper error envelope.
    
    Returns 429 Too Many Requests with error details.
    """
    error_id = get_request_id(request)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": {
                "code": ErrorCode.RATE_LIMIT_EXCEEDED.value,
                "message": "Rate limit exceeded. Please retry after some time.",
                "error_id": error_id,
                "details": {"retry_after": exc.detail if hasattr(exc, "detail") else None}
            }
        },
        headers={"X-Request-ID": error_id},
    )


# Rate limit configurations by endpoint type
# Format: "requests/period" where period is one of: second, minute, hour, day

# Permissive limits for interactive APIs
SEARCH_LIMIT = "30/minute"  # Search is CPU-intensive
CONVERSATION_LIMIT = "20/minute"  # Conversational Q&A is LLM-intensive
REFRESH_LIMIT = "10/minute"  # Refresh operations trigger background work
SUMMARY_READ_LIMIT = "60/minute"  # Read-only cache hits are cheap

# Setup/auth endpoints — tighter controls to prevent brute force
AUTH_REGISTRATION_LIMIT = "5/hour"  # Prevent registration abuse
AUTH_LOGIN_LIMIT = "10/minute"  # Reasonable for login attempts

# Firm/client metadata — moderate access
FIRMS_LIMIT = "100/minute"
CLIENTS_LIMIT = "100/minute"

# Task operations — prevent queue spam
TASK_SUBMIT_LIMIT = "50/minute"
TASK_STATUS_LIMIT = "100/minute"

# Email operations — moderate throughput
EMAIL_RETRIEVE_LIMIT = "100/minute"
EMAIL_CREATE_LIMIT = "50/minute"
