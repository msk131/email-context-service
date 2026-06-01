# File Q&A Guide

This guide mirrors the project structure and gives quick talking points for each
file. Use it during review when someone asks, "where is this implemented?" or
"why did you choose this layer?"

## Root

- `README.md` - Project overview, business problem, API examples, local run steps,
  and frontend integration notes. Use this to explain the product flow end to end.
- `docker-compose.yml` - Local multi-service setup for API replicas, Nginx, and
  Prometheus-style production simulation.
- `Dockerfile` - Runtime image for the FastAPI application.
- `Dockerfile.test` - Test image used by CI to prove the app can install and run
  tests in a clean container.
- `requirements.txt` - Runtime dependencies: FastAPI, SQLAlchemy, JWT, crypto,
  HTTP client, metrics, rate limiting, and migration tools.
- `requirements-test.txt` - Test/lint dependencies such as pytest, ruff, black,
  and test helpers.
- `pytest.ini` - Pytest config. Keeps test command behavior consistent locally
  and in CI.
- `alembic.ini` - Alembic migration config.
- `locustfile.py` - Load-test script for simulating users hitting auth, clients,
  summaries, refresh, and reports. Good talking point for performance mindset,
  though it should be aligned with seeded users/routes before relying on results.

## `.github`

- `.github/workflows/ci.yml` - CI pipeline. Installs dependencies, builds the test
  Docker image, runs tests, ruff, and black check on push/PR.
- `.github/copilot-instructions.md` - Local AI/editor guidance. Not part of app
  runtime; can be ignored for product architecture.

## `docs`

- `docs/ARCHITECTURE.md` - Main architecture explanation: workflow, layers, data
  model, caching, AI, scaling, indexes, and testing strategy.
- `docs/CHECKLIST.md` - Requirement-to-implementation mapping. Best file to open
  when asked whether a take-home criterion is covered.
- `docs/FILE_QA_GUIDE.md` - This file. Your quick memory map for Q&A.

## `infra`

- `infra/nginx.conf` - Reverse proxy/load-balancing config for multiple API
  replicas in Docker Compose.
- `infra/prometheus.yml` - Prometheus scrape config for the app metrics endpoint.

## `scripts`

- `scripts/email_flow_smoke.sh` - Smoke-test style script for walking through the
  email flow from the shell. Useful for demo preparation.

## `migrations`

- `migrations/env.py` - Alembic environment setup. Connects migrations to app DB
  metadata.
- `migrations/script.py.mako` - Alembic template used when generating migration
  files.
- `migrations/versions/20260529_0001_initial_schema.py` - Initial schema for the
  core entities: firms, users, clients, emails, summaries, logs, and tasks.
- `migrations/versions/20260529_0002_email_is_read_boolean.py` - Schema adjustment
  to store email read state as a proper boolean.
- `migrations/versions/20260529_0003_background_task_uuid.py` - Adds/adjusts task
  UUID support for background task tracking.
- `migrations/versions/20260529_0004_email_captured_at.py` - Adds captured time so
  partial refresh can count newly ingested emails since the last summary refresh.

## `app`

- `app/main.py` - FastAPI entry point. Creates the app, attaches middleware,
  exception handlers, and registers all routers.
- `app/__init__.py` - Package marker.

## `app/api`

- `app/api/__init__.py` - API package marker.
- `app/api/health.py` - Health endpoint for uptime checks.
- `app/api/metrics.py` - Prometheus-compatible metrics endpoint.

## `app/api/dependencies`

- `app/api/dependencies/__init__.py` - Dependency package marker.
- `app/api/dependencies/auth.py` - JWT authentication and role dependency helpers.
  This is where protected endpoints get the current user and enforce roles.

## `app/api/v1`

- `app/api/v1/__init__.py` - Versioned API package marker.
- `app/api/v1/auth.py` - Register and login endpoints. Handles bootstrap
  superuser flow and token issuing through the auth service.
- `app/api/v1/firms.py` - Firm CRUD endpoints. Superuser can manage firms; firm
  admins can update their own firm where allowed.
- `app/api/v1/clients.py` - Client CRUD endpoints with firm-scoped authorization.
- `app/api/v1/emails.py` - Reads stored emails for a client after authorization.
- `app/api/v1/mock_emails.py` - Mock Microsoft Graph-style email ingestion.
  Creates sent/received email rows and queues summary work.
- `app/api/v1/summaries.py` - Summary API surface: read cached summaries, enqueue
  refreshes, search, firm report, and global report.
- `app/api/v1/conversation.py` - Conversational Q&A endpoint over accessible
  email context.
- `app/api/v1/tasks.py` - Generic task endpoints. Used to enqueue summary work and
  poll task status.

## `app/cache`

- `app/cache/__init__.py` - Exposes cache helpers to the rest of the app.
- `app/cache/lru.py` - Small TTL/LRU summary response cache implementation.

## `app/common`

- `app/common/__init__.py` - Common package marker.
- `app/common/error_codes.py` - Shared error code constants.
- `app/common/error_handlers.py` - FastAPI exception handlers for consistent API
  error responses.
- `app/common/exceptions.py` - Domain exceptions such as not found or unauthorized.
- `app/common/models.py` - Shared ORM base and enums used by models.
- `app/common/rate_limit.py` - Rate-limit setup and endpoint-specific limits.
- `app/common/schemas.py` - Shared Pydantic schemas and role enum used by APIs.
- `app/common/time.py` - UTC time helper to avoid scattered datetime logic.

## `app/core`

- `app/core/__init__.py` - Exposes settings/config conveniences.
- `app/core/app_config.py` - FastAPI app factory, static docs styling, and
  exception-handler setup.
- `app/core/config.py` - Compatibility config module.
- `app/core/logging_config.py` - Logging setup and named logger helper.
- `app/core/middleware.py` - Request middleware such as request IDs.
- `app/core/request_handlers.py` - Request/exception helper behavior.
- `app/core/setting.py` - Pydantic settings from environment variables. Defines
  DB URL, JWT settings, cache limits, CORS, LLM model/API key, and encryption key.

## `app/db`

- `app/db/__init__.py` - DB package marker.
- `app/db/database.py` - Async SQLAlchemy engine/session setup and dependency for
  FastAPI routes.
- `app/db/session.py` - Session compatibility wrapper.

## `app/llm`

- `app/llm/__init__.py` - Exposes the LLM service.
- `app/llm/service.py` - Gemini-compatible summarization adapter. Builds prompts,
  calls the provider with retry/backoff, parses JSON, tracks tokens, and supports
  mock mode when no API key is configured.
- `app/llm/prompts.py` - Loads and renders YAML prompt templates.
- `app/llm/prompts.yml` - Prompt text for extracting actors, concluded
  discussions, open action items, and summary text.
- `app/llm/embeddings.py` - Lightweight embedding helper/fallback used for search
  and ranking without heavy ML dependencies.

## `app/models`

- `app/models/__init__.py` - Imports model classes so Alembic/SQLAlchemy can see
  metadata.
- `app/models/user.py` - `User` ORM model and single-firm compatibility helpers.
- `app/models/firm_membership.py` - `FirmMembership` ORM model. `user_id` is
  unique, so each non-superuser has at most one firm membership with a role.
- `app/models/accountant.py` - Accountant profile model for accountant-specific
  business data tied to a user's single firm membership.
- `app/models/firm.py` - `Firm` ORM model.
- `app/models/client.py` - `Client` ORM model with firm relationship and unique
  client email constraints.
- `app/models/email.py` - Stored email message model.
- `app/models/email_summary.py` - Encrypted latest summary per client.
- `app/models/summarization_log.py` - Per-call token and email-count tracking.
- `app/models/background_task.py` - DB-backed task model with status, payload,
  result, timestamps, and expiry.

## `app/repositories`

- `app/repositories/__init__.py` - Repository package marker.
- `app/repositories/users.py` - User lookup and user count queries for login and
  bootstrap registration.
- `app/repositories/firms.py` - Firm CRUD queries.
- `app/repositories/clients.py` - Client CRUD/list queries and firm filtering.
- `app/repositories/emails.py` - Email read/search queries, including date-range
  summary inputs and newly captured email counts.
- `app/repositories/email_summaries.py` - Summary record and summary coverage
  report queries.
- `app/repositories/tasks.py` - Task queue queries: create, fetch, claim, update,
  and cleanup expired tasks.

## `app/schemas`

- `app/schemas/__init__.py` - Schema package marker.
- `app/schemas/auth.py` - Register, login, token, and user response schemas.
- `app/schemas/firms.py` - Firm request/response schemas.
- `app/schemas/clients.py` - Client create/update/read schemas.
- `app/schemas/emails.py` - Email read and mock email capture schemas.
- `app/schemas/summaries.py` - Summary response, refresh task, search, and report
  schemas.
- `app/schemas/conversation.py` - Conversation request and response schemas.
- `app/schemas/tasks.py` - Background task request/status/response schemas.

## `app/services`

- `app/services/__init__.py` - Service package marker.
- `app/services/auth.py` - Auth business logic: password hashing, verification,
  bootstrap rules, role-based registration, firm creation, and JWT creation.
- `app/services/firms.py` - Firm business rules and authorization around firm
  access/update/delete.
- `app/services/clients.py` - Client business rules, including firm-scoped access
  checks.
- `app/services/emails.py` - Mock email send/receive workflows and client email
  read behavior.
- `app/services/summaries.py` - Summary use cases: authorized cached reads,
  refresh generation, partial refresh skip, LLM calls, encryption, reports, and
  summary-refresh task enqueueing.
- `app/services/tasks.py` - Generic task creation/status service logic and access
  checks.
- `app/services/email_search.py` - Natural-language/keyword email search over
  authorized emails.
- `app/services/conversation.py` - Conversational question-answer flow over email
  context.

## `app/tasks`

- `app/tasks/worker.py` - Background worker loop. Claims queued tasks, runs
  summary refresh work, stores task results/errors, and handles task cleanup.

## `app/utils`

- `app/utils/__init__.py` - Exposes utility helpers.
- `app/utils/helpers.py` - AES-GCM encryption/decryption and date-range
  normalization. This supports encrypted summary storage and invalid range
  rejection.

## `app/static`

- `app/static/swagger-custom.css` - Custom CSS for API docs styling.

## `tests`

- `tests/conftest.py` - Shared test fixtures and test DB/app setup.

## `tests/api`

- `tests/api/__init__.py` - API test package marker.
- `tests/api/test_main.py` - App-level route and startup behavior tests.
- `tests/api/test_request_id_middleware.py` - Verifies request ID middleware.
- `tests/api/test_setup_background_tasks.py` - Tests background task setup flow.
- `tests/api/test_summaries.py` - Summary API behavior tests.
- `tests/api/test_tasks.py` - Task endpoint tests.

## `tests/cache`

- `tests/cache/__init__.py` - Cache test package marker.
- `tests/cache/test_cache.py` - Cache behavior tests.

## `tests/common`

- `tests/common/__init__.py` - Common test package marker.
- `tests/common/test_exceptions.py` - Domain/API exception behavior tests.
- `tests/common/test_rate_limiting.py` - Rate-limit configuration tests.

## `tests/core`

- `tests/core/__init__.py` - Core test package marker.
- `tests/core/test_settings.py` - Settings validation tests.

## `tests/db`

- `tests/db/__init__.py` - DB test package marker.
- `tests/db/test_database.py` - Database/session setup tests.

## `tests/llm`

- `tests/llm/__init__.py` - LLM test package marker.
- `tests/llm/test_llm.py` - LLM parsing/mock behavior tests.
- `tests/llm/test_llm_services.py` - LLM service behavior tests.

## `tests/models`

- `tests/models/__init__.py` - Model test package marker.

## `tests/repositories`

- `tests/repositories/__init__.py` - Repository test package marker.

## `tests/schemas`

- `tests/schemas/__init__.py` - Schema test package marker.
- `tests/schemas/test_email_schemas.py` - Email schema validation tests.

## `tests/services`

- `tests/services/__init__.py` - Service test package marker.
- `tests/services/test_auth.py` - Auth service tests.
- `tests/services/test_auth_registration.py` - Bootstrap/admin registration rule
  tests.
- `tests/services/test_clients.py` - Client service and authorization tests.
- `tests/services/test_search_features.py` - Search/conversation feature tests.
- `tests/services/test_summaries.py` - Summary service tests, including encryption,
  refresh, and skip-style behavior.

## `tests/tasks`

- `tests/tasks/test_task_ttl_cleanup.py` - Task expiry/cleanup tests.

## `tests/utils`

- `tests/utils/__init__.py` - Utils test package marker.
- `tests/utils/test_utils.py` - Encryption and date-range utility tests.

## Fast Answers During Review

- "Where is authentication?" - `app/api/dependencies/auth.py`,
  `app/services/auth.py`, and `app/api/v1/auth.py`.
- "Where is authorization?" - Route dependencies plus service-level checks in
  `app/services/clients.py`, `app/services/firms.py`, and `app/services/tasks.py`.
- "Where is summary encryption?" - `app/utils/helpers.py` encrypts/decrypts;
  `app/services/summaries.py` writes encrypted text and decrypts for authorized
  responses.
- "Where is Gemini used?" - `app/llm/service.py`.
- "Where is prompt design?" - `app/llm/prompts.yml` and `app/llm/prompts.py`.
- "Where is retry/backoff?" - `app/llm/service.py` in `_call_provider`.
- "Where is partial refresh?" - `app/services/summaries.py`.
- "Where is caching?" - `app/cache/lru.py` and `app/services/summaries.py`.
- "Where is tracking?" - `EmailSummary` and `SummarizationLog` in
  `app/models/email_summary.py` and `app/models/summarization_log.py`; writes
  happen in `app/services/summaries.py`.
- "Where are reports?" - `app/api/v1/summaries.py`,
  `app/services/summaries.py`, and `app/repositories/email_summaries.py`.
- "Where is background work?" - `app/api/v1/tasks.py`,
  `app/services/summaries.py`, `app/services/tasks.py`, `app/repositories/tasks.py`,
  and `app/tasks/worker.py`.
- "Where is production readiness?" - Docker files, `.github/workflows/ci.yml`,
  `infra/*`, `app/api/metrics.py`, `app/common/rate_limit.py`, and
  `app/core/middleware.py`.
