# Observability

## Tools

- Request ID middleware
- Structured logging helpers
- Prometheus client
- Health endpoints

## Purpose

Observability provides traceability, service health visibility, and metrics for
runtime behavior such as request handling and LLM usage.

## Where It Lives

- Request IDs: `app/core/middleware.py`, `app/core/request_handlers.py`
- Logging: `app/core/logging_config.py`
- Metrics route: `app/api/metrics.py`
- Health routes: `app/api/health.py`
- LLM metrics: `app/llm/service.py`

## Design Notes

- `X-Request-ID` is accepted from callers or generated per request.
- Error responses include request IDs for support lookup.
- `/healthz` validates service dependencies.
- `/metrics` exposes Prometheus-compatible metrics.
