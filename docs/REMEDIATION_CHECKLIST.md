# Remediation Checklist

This checklist tracks the architecture and best-practice review findings that
need code changes. Items should be fixed in priority order, with tests updated
beside each fix.

## P0 - Security and Data Isolation

- [x] Require authentication for all non-bootstrap registrations.
  - Files: `app/services/auth.py`, `app/api/v1/setup.py`, auth tests.
  - Why: unauthenticated users should not be able to create accounts after the
    first bootstrap superuser exists.

- [x] Enforce firm-scoped authorization during mock email capture.
  - Files: `app/services/emails.py`, `app/api/v1/setup.py`, email/setup tests.
  - Why: users must not be able to inject email records into another firm's
    client context.

- [x] Make background task claiming atomic.
  - Files: `app/repositories/tasks.py`, `app/tasks/worker.py`, task tests.
  - Why: multiple workers or API background tasks can otherwise process the same
    pending task more than once.

## P1 - Persistence and Production Readiness

- [x] Replace startup `Base.metadata.create_all` with migrations.
  - Files: `app/main.py`, new Alembic migration files, docs.
  - Why: production schema changes need versioning, review, rollback, and
    repeatable deployment.

- [x] Add database uniqueness for `(firm_id, external_email)`.
  - Files: `app/models/clients.py`, migrations, client tests.
  - Why: service-level duplicate checks are not safe under concurrent writes.

- [x] Use proper database column types and nullability.
  - Files: `app/models/summaries.py`, migrations, email tests.
  - Why: `Email.is_read` should be Boolean, and email records should not allow
    orphan `client_id` values when all service logic assumes a client.

- [x] Standardize timezone-aware UTC timestamps.
  - Files: models, repositories, services, task worker.
  - Why: `DateTime(timezone=True)` should not be populated with naive
    `datetime.utcnow()` values.

- [x] Pin runtime dependencies or move dependency metadata into `pyproject.toml`.
  - Files: `requirements.txt`, `pyproject.toml`, Docker/CI docs.
  - Why: unpinned dependencies make builds less reproducible.

## P2 - Modularity and Maintainability

- [x] Split `app/services/summaries.py` by responsibility.
  - Candidate modules: summary generation, summary cache mapping, email search,
    conversation parsing, and summary reports.
  - Why: the current module mixes LLM orchestration, search, NLP parsing,
    encryption, caching, persistence, and response mapping.

- [x] Move report SQL out of API route handlers.
  - Files: `app/api/v1/summaries.py`, `app/services/summaries.py`,
    `app/repositories/summaries.py`.
  - Why: route handlers should validate, authorize, and delegate.

- [x] Keep transaction boundaries in services, not repositories.
  - Files: repositories and services that call `commit`.
  - Why: business workflows should commit or roll back as one unit.
  - Progress: client and firm repositories now flush only; task/email flows
    now commit at the service/worker boundary while task creation flushes.

- [x] Consolidate duplicate DB session modules.
  - Files: `app/db/database.py`, `app/db/session.py`, imports.
  - Why: two engine/session definitions can drift and confuse ownership.

- [x] Split setup/demo routes from auth routes.
  - Files: `app/api/v1/setup.py`, new `auth.py` or `mock_emails.py`.
  - Why: login/register and demo ingestion are separate API responsibilities.

- [x] Move in-memory search scoring out of repositories.
  - Files: `app/repositories/summaries.py`, search service/module.
  - Why: repositories should focus on data access, while ranking logic belongs
    in service/search code.

- [x] Move task payload validation and authorization out of API route handlers.
  - Files: `app/api/v1/tasks.py`, new task service/schema modules.
  - Why: routes should not parse arbitrary dictionaries or own business rules.

- [x] Keep FastAPI-specific dependencies out of business services.
  - Files: `app/services/auth.py`, service modules, API dependency modules.
  - Why: services should be reusable outside HTTP contexts and easier to unit
    test with domain exceptions.

- [x] Keep API package imports lightweight.
  - Files: `app/api/v1/__init__.py`, `app/main.py`, tests.
  - Why: importing one route module should not import every optional runtime
    dependency.

- [x] Standardize all response DTO mapping outside persistence code.
  - Files: service modules, schemas, repositories.
  - Why: repositories should not know about API response shapes.

- [ ] Replace Python-side vector scan with scalable search implementation.
  - Files: `app/repositories/summaries.py`, search service, database indexes.
  - Why: loading and scoring all rows in Python will not scale to production
    volumes and currently ranks emails by client summary embedding.

## Verification

- [x] `python3 -m ruff check app tests migrations`
- [x] `python3 -m pytest -q`
