# Architecture

This backend is a modular monolith for the Ascend Email Context case study. It is organized to make the business workflow easy to follow: ingest mock emails, authorize access to a client, summarize that client's context, cache reads, and report on summary coverage.

## Business Workflow

1. A firm, users, and clients are created through setup/demo endpoints.
2. Mock email rows simulate Microsoft Graph ingestion.
3. Mock email ingestion enqueues a non-forced `summarize_client` task; manual refresh can enqueue the same task with `force=true`.
4. The worker loads authorized emails, normalizes the optional date range, and applies the partial refresh rule.
5. The configured LLM provider produces structured summary data: actors, concluded discussions, open action items, and summary text.
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
Infrastructure     app/db, app/core, app/cache, app/llm, app/tasks, app/utils
```

Routes are intentionally thin. They validate input, bind FastAPI dependencies, enforce roles, and call services. Services own workflow decisions such as authorization orchestration, skip behavior, LLM calls, encryption, logging, and cache invalidation.

## Module Map

```text
app/
  api/
    health.py             Health check
    v1/
      setup.py            Bootstrap accounts, login, mock email ingestion
      clients.py          Client CRUD
      firms.py            Firm CRUD
      emails.py           Client email reads
      summaries.py        Summary reads, refresh enqueueing, search, conversation, reports
      tasks.py            Background task submission and status
  services/
    auth.py               JWT, credential hashing, RBAC, registration
    clients.py            Client lookup and firm-scoped authorization
    emails.py             Mock email creation and stored email reads
    firms.py              Firm lookup
    summaries.py          Summarization, search, conversation, reporting helpers
  repositories/           Focused SQLAlchemy queries
  models/                 Firm, Accountant, Client, Email, EmailSummary, SummarizationLog
  schemas/                Pydantic request and response models
  llm/                    LLM service and mock fallback
  tasks/                  DB-backed summarization worker
  cache/                  TTL/LRU summary response cache
  utils/                  Encryption and date helpers
```

## API Boundaries

Setup/demo endpoints:

- `POST /api/v1/setup/register`
- `POST /api/v1/setup/token`
- `POST /api/v1/setup/mock-emails/send`
- `POST /api/v1/setup/mock-emails/receive`

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
- `POST /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`

There is no separate production `auth` router in this case-study implementation. Login lives under `setup` with bootstrap and mock ingestion because those endpoints support the demo environment.

## Data Model

| Model | Notes |
| --- | --- |
| `Firm` | Parent organization for firm-scoped users and clients. |
| `Accountant` | Authenticated account with credential hash, role, and firm id. |
| `Client` | External client attached to one firm. |
| `Email` | Stored email message for a client. Includes sender, recipients, timestamp, subject, body, and direction. |
| `EmailSummary` | One latest summary per client. Summary text is encrypted at rest. |
| `SummarizationLog` | Per-call tracking for email count, token usage, and completion time. |

## Summarization Design

Manual refresh requests enqueue a `summarize_client` task and return `202` with
`task_id`. The worker calls `refresh_client_summary()`, which coordinates the
core workflow:

- normalize optional `start_date` and `end_date`
- reject logically invalid ranges
- skip re-summarization when fewer than 5 new emails arrived, unless `force=true`
- call the configured LLM provider with retry and exponential backoff
- keep the previous summary intact if the LLM provider fails
- encrypt the new summary text before saving
- write token usage and analyzed email count
- invalidate cache after a successful refresh

## Security Model

Roles:

- `accountant`: can access clients and emails inside their own firm.
- `firm_admin`: can access firm-scoped data, create users in their firm, and view firm coverage reports.
- `superuser`: can create users across firms and view global reports.

Security controls:

- bcrypt credential hashing
- JWT bearer authentication
- route-level role dependencies
- firm-scoped client authorization
- AES-GCM encryption for stored summary text
- no plaintext summary body persisted in `EmailSummary`

## Caching

Summary reads use an in-process TTL/LRU cache keyed by client id. This is enough for the exercise and keeps the API simple. A production deployment with multiple API instances should replace this with Redis or another shared cache while preserving the same service interface.

The cache stores the built summary API response in memory. The durable
LLM-result cache is the `email_summaries` table; normal summary reads do not
call the LLM.

## AI Integration

The LLM layer asks for structured JSON containing:

- `actors`
- `concluded_discussions`
- `open_action_items`
- `summary_text`

The service records token usage for cost visibility. When `LLM_API_KEY` is missing, local development uses a mock response so tests and demos can run without a network dependency.

## Scale Considerations

For the stated scale of 50 firms, around 10,000 clients per firm, and around 100 emails per client:

- email queries should remain client-scoped and timestamp-indexed
- summary refresh is queued in background tasks; production deployments should run a dedicated worker process
- reporting should aggregate by firm and summary existence rather than scanning email bodies
- cache should move to Redis for multi-instance deployments
- LLM calls should be rate-limited and queued if refresh volume increases

## Database Indexes

Indexes currently defined in the ORM:

| Index | Purpose |
| --- | --- |
| `ix_clients_firm_id` | Fast firm-scoped client filtering for authorization and reports. |
| `ix_emails_client_sent_at` | Fast client timeline reads and date-range summary refreshes. |
| `ix_emails_subject` | Basic subject lookup/search support. |
| `ix_emails_sender_address` | Sender-based lookup/search support. |
| `uq_email_summary_client` | Ensures one latest summary row per client. |
| `ix_summarization_logs_client_completed` | Efficient per-client summarization history and tracking. |
| `background_tasks.expires_at` | Efficient cleanup of completed/expired background tasks. |

For a production 10x scale-up, the next likely index additions would be a
client email uniqueness constraint per firm and a dedicated full-text/vector
search index for email content.

## Docker Scaling

The Compose setup runs API replicas behind Nginx and exposes Prometheus metrics.
Local scale commands:

```bash
docker compose up --build -d --scale api=10
docker compose up -d --scale api=15
```

Docker Compose does not provide native metric-based autoscaling. In production,
use the same image and `/metrics` endpoint with Kubernetes HPA, Docker Swarm, or
another scheduler to scale between 10 and 15 API instances based on CPU, memory,
request latency, or Prometheus custom metrics.

## Testing Strategy

Tests focus on the parts that protect production behavior:

- auth token creation and role handling
- cache TTL and invalidation
- email schema validation
- LLM parsing/mock behavior
- search and utility behavior
- background task lifecycle and cleanup

Run:

```bash
.venv/bin/python -m pytest -q
```
