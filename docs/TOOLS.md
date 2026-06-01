# Tooling By Purpose

This directory explains the main tools used in the service and why each exists.
Each page is intentionally short: purpose, where it appears in the codebase,
and operational notes.

| Purpose | Tooling | Doc |
| --- | --- | --- |
| API layer | FastAPI, Uvicorn, Pydantic | [api.md](tools/api.md) |
| Data persistence | SQLAlchemy, Alembic, PostgreSQL, SQLite | [database.md](tools/database.md) |
| Indexing | Relational indexes, uniqueness constraints, pgvector index | [indexes.md](tools/indexes.md) |
| Caching and serialization | Redis, orjson, local fallback cache | [cache.md](tools/cache.md) |
| Vector retrieval | Azure AI Search, pgvector, vectorizer module | [vectorizer.md](tools/vectorizer.md) |
| AI/report generation | LLM provider adapter, prompt YAML, embeddings | [ai.md](tools/ai.md) |
| Security | JWT, bcrypt, AES-GCM, CORS, rate limiting | [security.md](tools/security.md) |
| Background processing | DB-backed task queue and worker loop | [background-tasks.md](tools/background-tasks.md) |
| Observability | Request IDs, structured logs, Prometheus metrics, health checks | [observability.md](tools/observability.md) |
| Testing and quality | pytest, pytest-asyncio, ruff, black, Docker | [testing.md](tools/testing.md) |
