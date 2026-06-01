# Database And Migrations

## Tools

- `SQLAlchemy asyncio`
- `Alembic`
- PostgreSQL in production
- SQLite for lightweight local tests

## Purpose

SQLAlchemy provides async ORM and query execution. Alembic manages schema
migrations. PostgreSQL is the production target; SQLite keeps local tests fast.

## Where It Lives

- Engine/session: `app/db/database.py`
- ORM models: `app/models/*`
- Repositories: `app/repositories/*`
- Migrations: `migrations/versions/*`

## Design Notes

- Repositories own query details; services do not hand-write route-level SQL.
- Connection pooling is configured for non-SQLite databases.
- Firm-scoped indexes and uniqueness constraints support authorization and reports.
- pgvector support is added through the `email_embeddings` table for vector fallback.
- Index details are documented in [indexes.md](indexes.md).
