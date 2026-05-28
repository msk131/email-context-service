# Quick Start

This guide gets the Email Context & Summarization System running locally and walks through the main case-study flow: bootstrap a user, insert mock email context, summarize it, search it, and report on coverage.

## Run The API

```bash
cd /Users/mani/Documents/email-context-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
uvicorn app.main:app --reload
```

Run tests in Docker:

```bash
docker build --file Dockerfile.test --tag email-context-service:test .
```


Open Swagger UI:

```text
http://localhost:8000/docs
```

## Environment

Set these values before running against PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/email_context
JWT_SECRET_KEY=dev-secret-key-minimum-32-characters
ENCRYPTION_KEY_HEX=00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
SUMMARY_CACHE_TTL_SECONDS=3600
SUMMARY_CACHE_MAX_ITEMS=512
```

`GEMINI_API_KEY` is optional for local demos. When it is missing, the LLM layer returns deterministic mock summaries.

## Demo Flow

### 1. Bootstrap The First User

When the database has no users, the first registration must create a `superuser`.

```bash
curl -X POST http://localhost:8000/api/v1/setup/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "superuser@example.org",
    "password": "Password123!",
    "role": "superuser",
    "firm_name": "Ascend Demo CPA"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/setup/token \
  -H "Content-Type: application/json" \
  -d '{"email": "superuser@example.org", "password": "Password123!"}'
```

Use the returned `access_token` in the commands below.

### 3. Insert A Mock Email Thread

This simulates Microsoft Graph ingestion for the case study.

```bash
curl -X POST http://localhost:8000/api/v1/setup/mock-email-threads \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Akshar Patel",
    "client_email": "akshar@example.org",
    "topic": "1099-INT filing blocker",
    "message_count": 6
  }'
```

The response includes `client_id`.

### 4. Generate A Summary

```bash
curl -X POST "http://localhost:8000/api/v1/summaries/<client_id>/refresh?force=true" \
  -H "Authorization: Bearer <token>"
```

### 5. Read The Cached Summary

```bash
curl -X GET http://localhost:8000/api/v1/summaries/<client_id> \
  -H "Authorization: Bearer <token>"
```

### 6. Search Email Context

```bash
curl -X GET "http://localhost:8000/api/v1/summaries/search?query=1099-INT&limit=10" \
  -H "Authorization: Bearer <token>"
```

### 7. Ask A Conversation Question

```bash
curl -X POST http://localhost:8000/api/v1/summaries/conversation \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is still blocking Akshar's return?",
    "client_id": <client_id>,
    "limit": 10
  }'
```

## Reports

Firm admin report:

```bash
curl -X GET http://localhost:8000/api/v1/summaries/reports/firm-summaries \
  -H "Authorization: Bearer <firm_admin_token>"
```

Superuser report:

```bash
curl -X GET http://localhost:8000/api/v1/summaries/reports/global-summaries \
  -H "Authorization: Bearer <superuser_token>"
```

## Cache And Refresh Behavior

- Summary reads use an in-memory TTL/LRU cache.
- A successful refresh invalidates the cached summary.
- By default, refresh skips re-summarization when fewer than 5 new emails arrived since the previous refresh.
- Add `force=true` to re-analyze anyway.
- `start_date` and `end_date` are optional; invalid ranges are rejected.

Example:

```bash
curl -X POST "http://localhost:8000/api/v1/summaries/<client_id>/refresh?start_date=2026-01-01T00:00:00&end_date=2026-12-31T23:59:59" \
  -H "Authorization: Bearer <token>"
```

## Testing

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check app tests
```

## Troubleshooting

`ModuleNotFoundError` on startup:

- Run commands from the project root: `/Users/mani/Documents/email-context-service`.
- Use `uvicorn app.main:app --reload`.

`Could not connect to database`:

- Confirm PostgreSQL is running.
- Confirm `DATABASE_URL` matches your local database.

`Invalid email or password`:

- Register the bootstrap user first.
- Login through `/api/v1/setup/token`.

`Insufficient permissions`:

- Accountants and firm admins are firm-scoped.
- Firm reports require `firm_admin`.
- Global reports require `superuser`.
