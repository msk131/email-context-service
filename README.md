# Email Context Service

Backend API for Ascend's "Email Context" scenario: a system that helps CPA
firms understand all email discussions between their accountants and a client
before anyone sends another redundant follow-up.

## Business Problem

Ascend represents a group of CPA firms. During tax preparation, multiple
accountants inside the same firm may communicate with the same client to gather
documents, clarify filing details, or resolve blockers.

Without a shared view of those conversations, accountants can easily miss what a
colleague already asked, what the client already answered, or what is still
blocking the return. That creates redundant questions, poor coordination inside
the firm, and a frustrating client experience.

## Solution

This project builds a unified email context layer for CPA firms. It captures
mock email discussions between firm accountants and clients, groups those
messages by client, and generates structured summaries so accountants can
quickly see:

- who has been involved in the conversation
- what has already been concluded
- what action items are still open
- the latest summarized context for a specific client

In production, the email ingestion layer would connect to Microsoft Graph API
for Outlook/Office 365. For this project, the service uses seeded mock emails
and local utilities to simulate email ingestion.

## Core Data Model

The persistence layer is designed around these entities:

| Entity | Description |
| --- | --- |
| `Firm` | The CPA organization using the system. |
| `Accountant` | A user within a firm, including accountant, firm admin, and superuser roles. |
| `Client` | The external client being serviced by a CPA firm. |
| `Email` | An individual email with sender, recipients, timestamp, subject, body, direction, and client ownership. |
| `EmailSummary` | Processed intelligence derived from a client's email thread. |
| `SummarizationLog` | Audit and usage record for summary generation. |

Scale assumption: roughly 50 firms, 10,000 clients per firm, and 100 emails per
client.

## What The API Supports

- Firm, accountant, client, email, summary, and summarization log persistence
- JWT authentication and role-based access control
- Mock email creation and seeded demo data
- Client-level email summary generation
- Cached summary reads and queued summary refreshes
- Natural-language context search and conversation endpoints
- Standardized error responses
- Prometheus-compatible `/metrics` endpoint
- Background task records and worker processing for LLM-backed refreshes

## Documentation

The documentation is intentionally small for reviewer clarity:

- [docs/CHECKLIST.md](docs/CHECKLIST.md) - requirement checklist and evaluation criteria mapping
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - architecture, data model, indexes, scaling, and tradeoffs
- [docs/REMEDIATION_CHECKLIST.md](docs/REMEDIATION_CHECKLIST.md) - engineering cleanup checklist from code review

## Run Locally

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
uvicorn app.main:app --reload
```

This project is tested with Python 3.12, matching the Docker images. The core
install avoids heavyweight ML wheels; install optional Hugging Face embeddings
with `pip install -r requirements-embeddings.txt` when using a Python/PyTorch
platform that supports them.

API docs: http://localhost:8000/docs

## Frontend Integration Guide

Base URL:

```text
http://localhost:8000
```

Authenticated requests must include:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

Roles:

| Role | Typical frontend permissions |
| --- | --- |
| `superuser` | Manage all firms, create users for any firm, view global reports. |
| `firm_admin` | Manage own firm users/clients, view own firm reports. |
| `accountant` | Work with clients and emails inside own firm. |

### 1. Bootstrap Or Register Users

The first user can register without a token and must be a `superuser`. After
that, registration requires an authenticated `firm_admin` or `superuser`.

```http
POST /api/v1/setup/register
```

First user example:

```json
{
  "email": "admin@example.org",
  "password": "Password123!",
  "role": "superuser",
  "firm_name": "Ascend Demo CPA"
}
```

Admin-created user example:

```json
{
  "email": "accountant@example.org",
  "password": "Password123!",
  "role": "accountant",
  "firm_id": 1
}
```

Response:

```json
{
  "id": 1,
  "email": "admin@example.org",
  "role": "superuser",
  "firm_id": 1
}
```

Frontend behavior:

- If this is a fresh environment, show bootstrap registration.
- After bootstrap, show user creation only to `superuser` and `firm_admin`.
- Store no password after submit.

### 2. Login

```http
POST /api/v1/setup/token
```

Request:

```json
{
  "email": "admin@example.org",
  "password": "Password123!"
}
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Frontend behavior:

- Save the token in your auth state.
- Send it as `Authorization: Bearer <jwt>` on protected calls.
- On `401`, clear auth state and send the user back to login.

### 3. Firms

List visible firms:

```http
GET /api/v1/firms
```

Create firm, superuser only:

```http
POST /api/v1/firms
```

```json
{
  "name": "Northside CPA"
}
```

Update own firm as `firm_admin`, or any firm as `superuser`:

```http
PATCH /api/v1/firms/{firm_id}
```

```json
{
  "name": "Northside CPA Group"
}
```

Frontend behavior:

- Superusers can show a firm switcher.
- Firm-scoped users usually see only their own firm.

### 4. Clients

List clients visible to current user:

```http
GET /api/v1/clients
```

Superusers may filter:

```http
GET /api/v1/clients?firm_id=1
```

Create client:

```http
POST /api/v1/clients
```

```json
{
  "name": "Akshar Patel",
  "external_email": "akshar@example.org",
  "firm_id": 1
}
```

For firm-scoped users, `firm_id` can be omitted; the API uses the user's firm.

Update client:

```http
PATCH /api/v1/clients/{client_id}
```

```json
{
  "name": "Akshar P.",
  "external_email": "akshar@example.org"
}
```

Delete client:

```http
DELETE /api/v1/clients/{client_id}
```

### 5. Mock Email Ingestion

Use these endpoints to simulate Microsoft Graph email capture. The client email
must already exist in the current user's accessible firm.

Outbound email from accountant to client:

```http
POST /api/v1/setup/mock-emails/send
```

```json
{
  "message": {
    "from": {
      "emailAddress": {
        "address": "accountant@example.org",
        "name": "John Accountant"
      }
    },
    "toRecipients": [
      {
        "emailAddress": {
          "address": "akshar@example.org",
          "name": "Akshar Patel"
        }
      }
    ],
    "sentDateTime": "2026-05-29T08:12:00Z",
    "body": {
      "contentType": "Text",
      "content": "Please send the missing 1099-INT."
    }
  }
}
```

Inbound email from client:

```http
POST /api/v1/setup/mock-emails/receive
```

```json
{
  "from": {
    "emailAddress": {
      "address": "akshar@example.org",
      "name": "Akshar Patel"
    }
  },
  "toRecipients": [
    {
      "emailAddress": {
        "address": "accountant@example.org",
        "name": "John Accountant"
      }
    }
  ],
  "receivedDateTime": "2026-05-29T09:00:00Z",
  "body": {
    "contentType": "Text",
    "content": "I uploaded the missing form."
  }
}
```

Response includes a background summary task:

```json
{
  "message": {},
  "summary_task_id": 42,
  "summary_task_status": "pending"
}
```

### 6. Emails

List recent stored emails for a client:

```http
GET /api/v1/emails/clients/{client_id}?limit=50
```

Use this for client timeline views.

### 7. Summary Refresh And Polling

Start or force summary refresh:

```http
POST /api/v1/summaries/{client_id}/refresh?force=true
```

Optional date filters:

```http
POST /api/v1/summaries/{client_id}/refresh?start_date=2026-01-01T00:00:00Z&end_date=2026-01-31T23:59:59Z
```

Response:

```json
{
  "task_id": 42,
  "status": "pending"
}
```

Poll task status:

```http
GET /api/v1/tasks/{task_id}
```

Successful task response includes `result`. Once the task succeeds, fetch the
summary:

```http
GET /api/v1/summaries/{client_id}
```

Frontend behavior:

- Show a loading state after refresh.
- Poll every 2-5 seconds until `succeeded` or `failed`.
- Stop polling on terminal states.

### 8. Search And Conversation

Search accessible email context:

```http
GET /api/v1/summaries/search?query=missing%201099&limit=25
```

Optional filters:

```http
GET /api/v1/summaries/search?query=extension&client_id=1&start_date=2026-01-01T00:00:00Z&end_date=2026-05-31T23:59:59Z
```

Ask a question over accessible context:

```http
POST /api/v1/summaries/conversation
```

```json
{
  "question": "What is still blocking Akshar's tax return?"
}
```

Use search for result lists and conversation for an answer plus source emails.

### 9. Reports

Firm admin or superuser summary coverage:

```http
GET /api/v1/summaries/reports/firm-summaries
```

Superuser global summary coverage:

```http
GET /api/v1/summaries/reports/global-summaries
```

### 10. Error Handling

Common statuses:

| Status | Meaning | Frontend action |
| --- | --- | --- |
| `401` | Missing/invalid token | Clear session and show login. |
| `403` | Role or firm access denied | Show permission error. |
| `404` | Entity not found | Show not-found state. |
| `409` | Duplicate firm/client/user | Show field-level conflict message. |
| `422` | Invalid request body/query | Show validation errors. |
| `429` | Rate limit exceeded | Show retry message and back off. |

Recommended frontend flow:

1. Bootstrap first superuser if needed.
2. Login and store token.
3. Load visible firms and clients.
4. Create/select a client.
5. Ingest mock emails or list existing emails.
6. Trigger summary refresh.
7. Poll task status.
8. Read summary, search context, or ask conversation questions.

## Run With Docker Compose

Create a local `.env` with environment-specific values, then run:

```bash
docker compose up --build -d
```

The API is served through Nginx at:

```text
http://localhost:8000
```

To run multiple API instances locally:

```bash
docker compose up -d --scale api=10
docker compose up -d --scale api=15
```

Prometheus metrics are available at:

```text
http://localhost:9090
```

Docker Compose supports manual replica scaling. For production metric-based
autoscaling, use the same image and `/metrics` endpoint with Kubernetes HPA,
Docker Swarm, or another scheduler.

## Background Tasks

Long-running summary refreshes run as `summarize_client` tasks. Calling
`POST /api/v1/summaries/{client_id}/refresh` returns a task id immediately, and
the API stores task state in the database. You can also enqueue the task
directly:

Mock email ingestion enqueues the same task automatically with `force=false`,
so it refreshes only when there is no summary yet or at least 5 new emails have
arrived since the last summary.

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "summarize_client",
    "payload": {
      "client_id": 1,
      "force": true
    }
  }'
```

Check task status with `GET /api/v1/tasks/{task_id}`. Run the polling worker in
a separate process:

```bash
python -m app.tasks.worker
```

## Metrics

Prometheus-compatible metrics are exposed at:

```text
http://localhost:8000/metrics
```

The endpoint is useful for local scraping and confirming API/runtime metrics
while exercising summary refresh and task flows.

## Prompt Configuration

LLM prompts live in [app/llm/prompts.yml](app/llm/prompts.yml). The
summarization service loads the `summarization` prompt through
[app/llm/prompts.py](app/llm/prompts.py), renders runtime values such as
`emails`, `start_date`, and `end_date`, then passes the rendered prompt to the
configured LLM provider. Update the YAML template to tune summarization behavior
without changing service code.
