# Package Reference

This file is a current reference for the package layout used by the Email Context & Summarization System.

## Top-Level Structure

```text
app/
  main.py                 FastAPI application factory and router registration
  api/
    health.py             Health check
    v1/
      setup.py            Bootstrap, login, mock email ingestion
      clients.py          Client API
      emails.py           Email API
      firms.py            Firm API
      summaries.py        Summary, refresh, search, conversation, reports
  services/
    auth.py               Auth business logic and RBAC
    clients.py            Client lookup and authorization
    emails.py             Mock email/thread workflows
    firms.py              Firm lookup
    summaries.py          Summary workflows and email context features
  repositories/
    auth.py               Accountant queries
    clients.py            Client queries
    emails.py             Email queries
    firms.py              Firm queries
    summaries.py          Summary queries
  models/
    auth.py               Accountant ORM model
    clients.py            Client ORM model
    firms.py              Firm ORM model
    summaries.py          Email, EmailSummary, SummarizationLog models
  schemas/
    auth.py               Auth, registration, token, user schemas
    clients.py            Client schemas
    emails.py             Email and mock ingestion schemas
    firms.py              Firm schemas
    summaries.py          Summary, report, search, conversation schemas
  common/
    models.py             SQLAlchemy base and shared enums
    schemas.py            Role and token schemas
    exceptions.py         HTTP exception helpers
  core/
    config.py             Pydantic settings
  db/
    database.py           Async engine and session dependency
    session.py            Session compatibility module
  llm/
    llm.py                Gemini integration
    gemini.py             Gemini integration compatibility module
  cache/
    cache.py              TTL cache
    lru.py                LRU cache compatibility module
  utils/
    utils.py              Encryption and date helpers
    helpers.py            Additional helpers
```

## Import Patterns

Prefer domain-specific imports:

```python
from app.services.summaries import refresh_client_summary, read_cached_summary
from app.services.auth import require_role, create_access_token
from app.schemas.summaries import SummaryResponse
from app.models.summaries import EmailSummary
from app.db.database import get_session
```

Compatibility re-exports exist for a few older imports, such as:

```python
from app.auth import create_access_token
from app.cache import get_summary_cache
from app.config import settings
```

New code should use the explicit package paths where possible.

## Dependency Direction

```text
api routes
  ↓
services
  ↓
repositories
  ↓
models/db

services also depend on:
  cache
  llm
  utils
  common schemas/exceptions
```

Routes should not contain business workflows. Repositories should not contain authorization or LLM behavior. Services are the coordination layer.

## Key Public Functions

Auth:

```python
authenticate_accountant(session, email, password)
create_access_token(data)
get_current_user(credentials, session)
get_optional_current_user(credentials, session)
register_accountant(session, ...)
require_role(*roles)
```

Summaries:

```python
refresh_client_summary(session, client_id, start_date, end_date, force=False)
read_cached_summary(session, client_id)
search_email_context(session, current_user, query, ...)
answer_email_context_question(session, current_user, question, ...)
```

Emails:

```python
list_client_emails(session, client_id, ...)
mock_send_email(session, current_user, request)
mock_send_thread(session, current_user, request)
```

Clients:

```python
authorize_client_for_user(current_user, client, role)
get_client(session, client_id)
```

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/email_context
JWT_SECRET_KEY=replace-with-a-long-random-secret
ENCRYPTION_KEY_HEX=00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
SUMMARY_CACHE_TTL_SECONDS=3600
SUMMARY_CACHE_MAX_ITEMS=512
```

## Testing Reference

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check app tests
```

The current test suite covers auth, cache behavior, email schemas, LLM behavior, search helpers, and utilities.
