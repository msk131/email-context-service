# Domain Boundaries

This project uses domain-oriented packages without a heavy DDD folder structure. The goal is practical separation: each business area has its own models, schemas, services, repositories, and routes where useful, while shared infrastructure remains centralized.

## Domains

| Domain | Responsibility | Main Files |
| --- | --- | --- |
| Auth and setup | Registration, login, JWTs, passwords, RBAC, demo bootstrap | `app/api/v1/setup.py`, `app/services/auth.py`, `app/schemas/auth.py`, `app/models/auth.py` |
| Firms | CPA organization metadata | `app/api/v1/firms.py`, `app/services/firms.py`, `app/models/firms.py` |
| Clients | External client records and firm-scoped access checks | `app/api/v1/clients.py`, `app/services/clients.py`, `app/models/clients.py` |
| Emails | Mock email ingestion and stored email reads | `app/api/v1/emails.py`, `app/services/emails.py`, `app/models/summaries.py` |
| Summaries | LLM summarization, cache, search, conversation, reports | `app/api/v1/summaries.py`, `app/services/summaries.py`, `app/schemas/summaries.py` |

## Shared Kernel

Shared code is intentionally small:

- `app/common/schemas.py`: role and token contracts
- `app/common/models.py`: SQLAlchemy base and shared enums
- `app/common/exceptions.py`: reusable HTTP exceptions
- `app/core/config.py`: application settings
- `app/db/database.py`: async session dependency

## Current Route Boundaries

```text
/api/v1/setup       bootstrap, login, mock data
/api/v1/firms       firm reads
/api/v1/clients     client reads
/api/v1/emails      email reads
/api/v1/summaries   summaries, refresh, search, conversation, reports
```

Login is intentionally under `/setup/token` in this case-study codebase because the auth workflow is part of the demo/bootstrap surface.

## Why This Shape

- The exercise is small enough for a modular monolith.
- Services keep business rules testable without route-level coupling.
- Repositories keep database access focused and reusable.
- Infrastructure code can be swapped later, such as Redis for cache or a worker queue for summarization.

## Future Extraction Points

If this grew beyond the take-home scale, the cleanest extraction points would be:

- background summarization worker for refresh jobs
- Redis-backed distributed summary cache
- reporting read model for large multi-firm dashboards
- dedicated ingestion service for Microsoft Graph webhooks
- LLM gateway for model routing, cost controls, and rate limiting
