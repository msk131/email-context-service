# Email Context Service

FastAPI backend for CPA firms to capture client email context, generate client
reports, search prior conversations, and answer questions without sending
duplicate follow-ups.

## Portfolio Project Summary

This project demonstrates my ability to design and build a production-style
backend service with secure multi-tenant access, AI-assisted retrieval, encrypted
report storage, observability, background processing, and clear schema ownership.

It is positioned as a hands-on engineering project focused on:

- FastAPI service architecture and API design
- Role-based access control for firm-scoped data
- SQLAlchemy schema design and repository patterns
- AI search and retrieval with fallback strategies
- Encrypted report generation and audit logging
- Redis caching, Prometheus metrics, and worker-based async processing
- Testable, maintainable backend delivery practices

## Business Problem

CPA firms often have several accountants communicating with the same client
during tax preparation. Without a shared email context, teams repeat questions,
miss already-provided documents, and lose track of unresolved blockers. This
service gives firm-scoped users a single place to review prior email context,
generate client reports, search historical messages, and ask grounded questions
before contacting the client again.

## What It Does

- JWT auth with `superuser`, `firm_admin`, and `accountant` roles.
- Firm-scoped client and email access control.
- Mock Microsoft Graph-style email ingestion for local development.
- LLM-backed client report generation with queued refresh tasks.
- Azure AI Search vector retrieval with pgvector fallback and DB keyword fallback.
- Redis-first caching with local fallback for tests/development.
- Prometheus metrics, request IDs, rate limiting, and structured error envelopes.

## Architecture

The codebase follows a layered FastAPI architecture:

```text
app/api/v1          Controllers: HTTP routes, request parsing, Depends wiring
app/services        Business logic: auth, clients, emails, reports, summaries
app/repositories    Data access: SQLAlchemy queries and persistence helpers
app/models          Database schema: ORM tables and relationships
app/schemas         API schema: Pydantic request/response contracts
app/vectorizer      Retrieval: Azure AI Search primary, pgvector fallback
app/cache           Caching: Redis-first JSON cache with local fallback
app/llm             AI layer: prompts, embeddings, LLM provider adapter
app/tasks           Worker layer: DB-backed async report refresh processing
```

Routes stay thin and call services. Services own authorization orchestration,
workflow decisions, LLM/vectorizer calls, cache invalidation, and transaction
boundaries. Repositories isolate database access so route handlers never contain
raw queries.

## Schema Design

The data model is centered on firm-scoped ownership:

| Table | Purpose |
| --- | --- |
| `firms` | CPA organizations. |
| `users` | Login identities and optional platform superuser role. |
| `firm_memberships` | Single-firm role assignment for firm admins/accountants. |
| `accountants` | Accountant business profile tied to a user membership. |
| `clients` | External clients owned by a firm; email is unique per firm. |
| `emails` | Captured inbound/outbound messages linked to one client. |
| `email_embeddings` | Per-email vector data for pgvector fallback retrieval. |
| `email_summaries` | Latest encrypted generated report for a client. |
| `summarization_logs` | Audit and token usage history for report generation. |
| `background_tasks` | Durable task queue state for async report refreshes. |

Important design choices:

- Firm-scoped authorization uses `firm_id` on clients and membership roles.
- Generated report text is encrypted at rest; metadata and token counts remain queryable.
- Email embeddings are separate from `emails` so vector indexing can evolve independently.
- Report coverage endpoints aggregate by client/report existence instead of scanning bodies.
- Redis caches derived API responses; database tables remain the source of truth.

Core workflow:

1. Create firms, users, and clients.
2. Capture sent/received mock emails for a registered client.
3. Store email embeddings for vector fallback retrieval.
4. Enqueue report refresh work.
5. Worker generates an encrypted client report.
6. Users read reports, search email context, or ask conversation questions.

## Run Locally

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

Run tests:

```bash
python3 -m pytest
```

Run the worker:

```bash
python3 -m app.tasks.worker
```

## Required Environment

```bash
DATABASE_URL=sqlite+aiosqlite:///./local.db
JWT_SECRET_KEY=change-me
ENCRYPTION_KEY_HEX=00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff
```

Useful production settings:

```bash
APP_ENV=production
REDIS_URL=redis://redis:6379/0
CORS_ALLOWED_ORIGINS=https://app.example.com
TRUSTED_HOSTS=api.example.com
LLM_API_KEY=<provider-key>
LLM_MODEL=gemini-2.5-flash

VECTORIZER_ENABLED=true
VECTORIZER_CACHE_ENABLED=true
AZURE_AI_SEARCH_ENDPOINT=https://<service>.search.windows.net
AZURE_AI_SEARCH_API_KEY=<search-key>
AZURE_AI_SEARCH_INDEX_NAME=email-context
PGVECTOR_ENABLED=true
```

## Main Endpoints

Authentication:

```http
POST /api/v1/auth/register
POST /api/v1/auth/token
```

Firms and clients:

```http
GET    /api/v1/firms
POST   /api/v1/firms
PATCH  /api/v1/firms/{firm_id}
GET    /api/v1/clients
POST   /api/v1/clients
PATCH  /api/v1/clients/{client_id}
DELETE /api/v1/clients/{client_id}
```

Email ingestion and timeline:

```http
POST /api/v1/mock-emails/send
POST /api/v1/mock-emails/receive
GET  /api/v1/emails/clients/{client_id}?limit=50
```

Client reports:

```http
POST /api/v1/summaries/{client_id}/refresh?force=true
GET  /api/v1/summaries/{client_id}
GET  /api/v1/tasks/{task_id}
```

Search, conversation, and reporting:

```http
GET  /api/v1/summaries/search?query=missing%201099&limit=25
POST /api/v1/conversation
GET  /api/v1/summaries/reports/firm-client-reports
GET  /api/v1/summaries/reports/global-client-reports
```

Health and metrics:

```http
GET /api/health
GET /api/healthz
GET /metrics
```

## Roles

| Role | Access |
| --- | --- |
| `superuser` | Platform-wide firms, users, clients, reports. |
| `firm_admin` | Own firm users, clients, emails, and firm reports. |
| `accountant` | Own firm clients, emails, reports, search, and conversation. |

The first registered user must be a `superuser`. After bootstrap, user creation
requires an authenticated `superuser` or `firm_admin`.

## Vectorizer Strategy

Search uses a layered retrieval strategy:

1. Azure AI Search hybrid/semantic vector retrieval when configured.
2. pgvector fallback through `email_embeddings`.
3. SQL keyword fallback for local development and empty vector results.

Search responses are cached through Redis when configured. If Redis is missing
or unavailable, the cache helper falls back to a bounded in-process cache so
tests and local development keep working.

## Docker Compose

```bash
docker compose up --build -d
```

API: http://localhost:8000

Prometheus: http://localhost:9090

Scale API replicas locally:

```bash
docker compose up -d --scale api=3
```

## More Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/TOOLS.md](docs/TOOLS.md)
- [docs/CHECKLIST.md](docs/CHECKLIST.md)
- [docs/FILE_QA_GUIDE.md](docs/FILE_QA_GUIDE.md)
