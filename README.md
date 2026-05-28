# Email Context & Summarization System

Backend API for Ascend's CPA email-context case study. The system gives accountants a shared view of client email conversations so teams can avoid duplicate questions, understand what has already been resolved, and identify the next action items before contacting a client.

## Business Problem

CPA firms often have multiple accountants communicating with the same client during tax preparation. One accountant may ask for a 1099-INT, another may already have received it, and a third may not know that the remaining blocker is a missing brokerage statement. Without a unified context layer, the firm creates extra work for staff and a frustrating experience for clients.

This backend solves that by storing client email history, summarizing the full thread for a client, and exposing searchable, role-protected context to accountants, firm admins, and Ascend superusers.

## Product Use Cases

- An accountant opens a client record and sees the latest summary of all firm-client email discussions.
- The summary highlights actors mentioned, concluded discussions, and open action items.
- A user refreshes the summary after new emails are ingested.
- The system skips unnecessary LLM work when fewer than 5 new emails arrived since the previous refresh.
- A firm admin checks how many clients in their firm have generated summaries.
- A superuser reviews summary coverage grouped by firm.
- A user searches email context with natural language, such as `show clients who had issues with 1099-INT filing`.
- A user asks a conversational question, such as `What is still blocking Akshar's return?`, and receives an answer grounded in source email snippets.

## Case Study Expectations

The implementation is designed around the take-home exercise pillars:

- **System design**: clean FastAPI routes, Pydantic contracts, service/repository separation, and clear role boundaries.
- **Database proficiency**: explicit firm, accountant, client, email, summary, and summarization log models with indexes for client email access and summary tracking.
- **AI integration**: Gemini summarization, structured JSON extraction, retry/backoff, mock fallback for local demos, and token usage tracking.
- **Production mindset**: JWT authentication, role-based authorization, encrypted summaries at rest, cache invalidation, partial refresh behavior, tests, and CI.

Scale target: 50 firms, around 10,000 clients per firm, and around 100 emails per client.

## Core Entities

| Entity | Purpose |
| --- | --- |
| `Firm` | CPA organization using the platform. |
| `Accountant` | Authenticated user inside a firm, with `accountant`, `firm_admin`, or `superuser` role. |
| `Client` | External client serviced by a CPA firm. |
| `Email` | Mocked email message with sender, recipients, timestamp, subject, body, direction, and client ownership. |
| `EmailSummary` | Encrypted LLM-derived summary for a client's email context. |
| `SummarizationLog` | Audit/cost record for each summarization call, including email count and token usage. |

## System Design

The app is a modular monolith with clear layer boundaries:

```text
app/
  api/v1/          HTTP routes and OpenAPI metadata
  services/        Business workflows and authorization orchestration
  repositories/    SQLAlchemy query helpers
  models/          ORM entities and indexes
  schemas/         Pydantic request/response contracts
  llm/             Gemini integration and mock fallback
  cache/           In-memory TTL/LRU summary cache
  utils/           Encryption and date helpers
  core/            Settings
  db/              Async SQLAlchemy engine/session
```

Route handlers stay thin. They validate input, enforce authentication/authorization, and delegate business behavior to services. Services coordinate repositories, cache, encryption, and LLM calls.

## API Surface

All product endpoints require `Authorization: Bearer <token>` except bootstrap registration and login.

### Setup And Mock Ingestion

These endpoints replace a production Microsoft Graph integration for the case study. They seed realistic data and simulate new email arrival.

- `POST /api/v1/setup/register`: bootstrap the first superuser, then create users as a firm admin or superuser.
- `POST /api/v1/setup/token`: login and receive a JWT bearer token.
- `POST /api/v1/setup/mock-emails`: insert one inbound or outbound mock email.
- `POST /api/v1/setup/mock-email-threads`: insert a realistic CPA/client thread for demos.

### Firm, Client, And Email Reads

- `GET /api/v1/firms/{firm_id}`: read firm metadata.
- `GET /api/v1/clients/{client_id}`: read an authorized client.
- `GET /api/v1/emails/clients/{client_id}`: list stored emails for an authorized client.

### Summarization

- `GET /api/v1/summaries/{client_id}`: read the latest summary from cache or database.
- `POST /api/v1/summaries/{client_id}/refresh`: re-analyze client emails and invalidate cache.

Refresh accepts:

- `start_date`: optional ISO datetime. Defaults to the earliest email when omitted.
- `end_date`: optional ISO datetime. Defaults to now when omitted.
- `force`: optional boolean. Defaults to `false`; when `true`, bypasses the fewer-than-5-new-emails skip rule.

Invalid date ranges are rejected. If Gemini fails after retries, the existing summary remains unchanged.

### Search And Conversation

- `GET /api/v1/summaries/search`: natural-language/keyword search across authorized email context.
- `POST /api/v1/summaries/conversation`: answer a question using matched email snippets as source context.

### Reporting

- `GET /api/v1/summaries/reports/firm-summaries`: firm admin report for clients with summaries in the admin's firm.
- `GET /api/v1/summaries/reports/global-summaries`: superuser report grouped by firm.

## Summarization Behavior

The summarization engine asks Gemini to return structured JSON with:

- `actors`: people or organizations mentioned in the thread.
- `concluded_discussions`: items that appear resolved.
- `open_action_items`: remaining requests, blockers, or follow-ups.
- `summary_text`: concise narrative summary for the accountant.

Each successful call records:

- client id
- emails analyzed
- refresh timestamp
- input token estimate/usage
- output token estimate/usage

## Security And Access Control

- Passwords are hashed with bcrypt.
- JWTs carry `sub`, `role`, `firm_id`, and `exp`.
- Accountants and firm admins can access only clients in their firm.
- Firm admins can create users only inside their own firm.
- Superusers can create users across firms and view global reports.
- Stored summary text is encrypted at rest with AES-GCM.
- Summary reads use cache, but refresh invalidates the cache after successful re-analysis.

## Local Setup

Prerequisites:

- Python 3.12+
- PostgreSQL for normal development
- Gemini API key for real summarization, optional for local testing

Install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
```

Run tests in Docker:

```bash
docker build --file Dockerfile.test --tag email-context-service:test .
```

Set environment variables:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/email_context
JWT_SECRET_KEY=replace-with-a-long-random-secret
ENCRYPTION_KEY_HEX=00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
SUMMARY_CACHE_TTL_SECONDS=3600
SUMMARY_CACHE_MAX_ITEMS=512
```

Run:

```bash
uvicorn app.main:app --reload
```

Swagger UI:

```text
http://localhost:8000/docs
```

## Demo Flow

Bootstrap the first superuser:

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

Login:

```bash
curl -X POST http://localhost:8000/api/v1/setup/token \
  -H "Content-Type: application/json" \
  -d '{"email": "superuser@example.org", "password": "Password123!"}'
```

Create a realistic email thread:

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

Refresh and read the summary:

```bash
curl -X POST "http://localhost:8000/api/v1/summaries/<client_id>/refresh?force=true" \
  -H "Authorization: Bearer <token>"

curl -X GET http://localhost:8000/api/v1/summaries/<client_id> \
  -H "Authorization: Bearer <token>"
```

## Testing And Quality

Run tests:

```bash
.venv/bin/python -m pytest -q
```

Run lint:

```bash
.venv/bin/python -m ruff check app tests
```

CI runs dependency installation, Ruff, and Pytest on push and pull requests via `.github/workflows/ci.yml`.
