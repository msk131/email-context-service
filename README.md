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
- Cached summary reads and forced refreshes
- Natural-language context search and conversation endpoints
- Standardized error responses
- Prometheus-compatible `/metrics` endpoint
- Background task records for async-style workflows

## Documentation

Quick start: [docs/QUICKSTART.md](docs/QUICKSTART.md)

- [docs/INITIAL_DATA.md](docs/INITIAL_DATA.md) - Initial DB data and script
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Architecture notes
- [docs/DDD_ARCHITECTURE.md](docs/DDD_ARCHITECTURE.md) - DDD design reasoning
- [docs/MODULE_MAP.md](docs/MODULE_MAP.md) - Module responsibilities
- [docs/PACKAGE_REFERENCE.md](docs/PACKAGE_REFERENCE.md) - Package and runtime details

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs
