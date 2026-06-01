# API Layer

## Tools

- `FastAPI`
- `Uvicorn`
- `Pydantic v2`

## Purpose

FastAPI exposes the HTTP API, binds dependencies with `Depends()`, and generates
OpenAPI docs. Uvicorn runs the ASGI app locally and in containers. Pydantic
defines request and response contracts.

## Where It Lives

- Routes: `app/api/v1/*`
- Shared dependencies: `app/api/dependencies/*`
- App setup: `app/main.py`, `app/core/app_config.py`
- Schemas: `app/schemas/*`

## Design Notes

- Routes stay thin and delegate business logic to `app/services`.
- Auth, database sessions, and rate limiting are injected through FastAPI dependencies.
- Response models protect API output shape and avoid leaking ORM internals.
