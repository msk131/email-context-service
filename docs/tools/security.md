# Security

## Tools

- `python-jose` for JWTs
- `bcrypt` for password hashing
- `cryptography` AES-GCM for encrypted report text
- FastAPI security dependencies
- `slowapi` for rate limiting
- CORS and trusted-host middleware

## Purpose

Security controls enforce authentication, authorization, firm scoping, safe
credential handling, encrypted sensitive report text, and request abuse limits.

## Where It Lives

- Auth dependencies: `app/api/dependencies/auth.py`
- Auth service: `app/services/auth.py`
- Encryption helpers: `app/utils/helpers.py`
- Rate limiting: `app/common/rate_limit.py`
- Middleware setup: `app/core/app_config.py`, `app/core/middleware.py`

## Design Notes

- Route access is role-scoped through `require_role(...)`.
- Services enforce firm/client ownership before reading sensitive data.
- CORS wildcard origins are rejected when credentialed CORS is enabled.
- Global exception handlers mask unhandled internal errors from clients.
