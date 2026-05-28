# Architecture

This backend is a modular monolith for the Ascend Email Context case study. It is organized to make the business workflow easy to follow: ingest mock emails, authorize access to a client, summarize that client's context, cache reads, and report on summary coverage.

## Business Workflow

1. A firm, users, and clients are created through setup/demo endpoints.
2. Mock email rows simulate Microsoft Graph ingestion.
3. An authenticated accountant, firm admin, or superuser requests a summary refresh for a client.
4. The service loads authorized emails, normalizes the optional date range, and applies the partial refresh rule.
5. Gemini produces structured summary data: actors, concluded discussions, open action items, and summary text.
6. Summary text is encrypted before persistence.
7. Token usage and email count are recorded for tracking.
8. Summary reads are served from cache when possible.

## Layering

```text
HTTP routes        app/api/v1/*
Business logic     app/services/*
Data access        app/repositories/*
ORM models         app/models/*
API contracts      app/schemas/*
Infrastructure     app/db, app/core, app/cache, app/llm, app/utils
```

Routes are intentionally thin. They validate input, bind FastAPI dependencies, enforce roles, and call services. Services own workflow decisions such as authorization orchestration, skip behavior, LLM calls, encryption, logging, and cache invalidation.

## Module Map

```text
app/
  api/
    health.py             Health check
    v1/
      setup.py            Bootstrap users, login, mock email ingestion
      clients.py          Client reads
      firms.py            Firm reads
      emails.py           Client email reads
      summaries.py        Summary, refresh, search, conversation, reports
  services/
    auth.py               JWT, password hashing, RBAC, registration
    clients.py            Client lookup and firm-scoped authorization
    emails.py             Mock email/thread creation
    firms.py              Firm lookup
    summaries.py          Summarization, search, conversation, reporting helpers
  repositories/           Focused SQLAlchemy queries
  models/                 Firm, Accountant, Client, Email, EmailSummary, SummarizationLog
  schemas/                Pydantic request and response models
  llm/                    Gemini service and mock fallback
  cache/                  TTL/LRU cache
  utils/                  Encryption and date helpers
```

## API Boundaries

Setup/demo endpoints:

- `POST /api/v1/setup/register`
- `POST /api/v1/setup/token`
- `POST /api/v1/setup/mock-emails`
- `POST /api/v1/setup/mock-email-threads`

Product endpoints:

- `GET /api/v1/firms/{firm_id}`
- `GET /api/v1/clients/{client_id}`
- `GET /api/v1/emails/clients/{client_id}`
- `GET /api/v1/summaries/{client_id}`
- `POST /api/v1/summaries/{client_id}/refresh`
- `GET /api/v1/summaries/search`
- `POST /api/v1/summaries/conversation`
- `GET /api/v1/summaries/reports/firm-summaries`
- `GET /api/v1/summaries/reports/global-summaries`

There is no separate production `auth` router in this case-study implementation. Login lives under `setup` with bootstrap and mock ingestion because those endpoints support the demo environment.

## Data Model

| Model | Notes |
| --- | --- |
| `Firm` | Parent organization for firm-scoped users and clients. |
| `Accountant` | User account with password hash, role, and firm id. |
| `Client` | External client attached to one firm. |
| `Email` | Stored email message for a client. Includes sender, recipients, timestamp, subject, body, and direction. |
| `EmailSummary` | One latest summary per client. Summary text is encrypted at rest. |
| `SummarizationLog` | Per-call tracking for email count, token usage, and completion time. |

## Summarization Design

`refresh_client_summary()` coordinates the core workflow:

- authorize access before reading client context
- normalize optional `start_date` and `end_date`
- reject logically invalid ranges
- skip re-summarization when fewer than 5 new emails arrived, unless `force=true`
- call Gemini with retry and exponential backoff
- keep the previous summary intact if Gemini fails
- encrypt the new summary text before saving
- write token usage and analyzed email count
- invalidate cache after a successful refresh

## Security Model

Roles:

- `accountant`: can access clients and emails inside their own firm.
- `firm_admin`: can access firm-scoped data, create users in their firm, and view firm coverage reports.
- `superuser`: can create users across firms and view global reports.

Security controls:

- bcrypt password hashing
- JWT bearer authentication
- route-level role dependencies
- firm-scoped client authorization
- AES-GCM encryption for stored summary text
- no plaintext summary body persisted in `EmailSummary`

## Caching

Summary reads use an in-process TTL/LRU cache keyed by client id. This is enough for the exercise and keeps the API simple. A production deployment with multiple API instances should replace this with Redis or another shared cache while preserving the same service interface.

## AI Integration

The Gemini layer asks for structured JSON containing:

- `actors`
- `concluded_discussions`
- `open_action_items`
- `summary_text`

The service records token usage for cost visibility. When `GEMINI_API_KEY` is missing, local development uses a mock response so tests and demos can run without a network dependency.

## Scale Considerations

For the stated scale of 50 firms, around 10,000 clients per firm, and around 100 emails per client:

- email queries should remain client-scoped and timestamp-indexed
- summary refresh should be demand-driven or moved to background workers
- reporting should aggregate by firm and summary existence rather than scanning email bodies
- cache should move to Redis for multi-instance deployments
- LLM calls should be rate-limited and queued if refresh volume increases

## Testing Strategy

Tests focus on the parts that protect production behavior:

- auth token creation and role handling
- cache TTL and invalidation
- email schema validation
- LLM parsing/mock behavior
- search and utility behavior

Run:

```bash
.venv/bin/python -m pytest -q
```
