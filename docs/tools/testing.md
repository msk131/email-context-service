# Testing And Quality

## Tools

- `pytest`
- `pytest-asyncio`
- `ruff`
- `black`
- Docker and Docker Compose

## Purpose

The test stack covers service logic, repositories, schemas, cache behavior,
request middleware, LLM parsing, and task lifecycle behavior.

## Where It Lives

- Tests: `tests/*`
- Test dependencies: `requirements-test.txt`
- Docker files: `Dockerfile`, `Dockerfile.test`, `docker-compose.yml`

## Design Notes

- Async tests use `pytest-asyncio`.
- SQLite keeps most test paths fast and isolated.
- External providers are mocked or bypassed through local fallback modes.
- Docker Compose is used for local integration-style runs and replica testing.
