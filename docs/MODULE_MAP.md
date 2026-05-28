# Module Map

This map shows where each case-study requirement lives in the codebase.

## API Entry Points

```text
app/main.py
  ├── /api                         app/api/health.py
  └── /api/v1
      ├── /setup                   app/api/v1/setup.py
      ├── /firms                   app/api/v1/firms.py
      ├── /clients                 app/api/v1/clients.py
      ├── /emails                  app/api/v1/emails.py
      └── /summaries               app/api/v1/summaries.py
```

## Business Capabilities

| Capability | Route | Main Service |
| --- | --- | --- |
| Bootstrap users | `POST /api/v1/setup/register` | `app/services/auth.py` |
| Login | `POST /api/v1/setup/token` | `app/services/auth.py` |
| Mock email ingestion | `POST /api/v1/setup/mock-emails` | `app/services/emails.py` |
| Mock thread ingestion | `POST /api/v1/setup/mock-email-threads` | `app/services/emails.py` |
| Client read | `GET /api/v1/clients/{client_id}` | `app/services/clients.py` |
| Email read | `GET /api/v1/emails/clients/{client_id}` | `app/services/emails.py` |
| Summary read | `GET /api/v1/summaries/{client_id}` | `app/services/summaries.py` |
| Summary refresh | `POST /api/v1/summaries/{client_id}/refresh` | `app/services/summaries.py` |
| Natural-language search | `GET /api/v1/summaries/search` | `app/services/summaries.py` |
| Conversation Q&A | `POST /api/v1/summaries/conversation` | `app/services/summaries.py` |
| Firm report | `GET /api/v1/summaries/reports/firm-summaries` | `app/api/v1/summaries.py` |
| Global report | `GET /api/v1/summaries/reports/global-summaries` | `app/api/v1/summaries.py` |

## Summarization Flow

```text
POST /api/v1/summaries/{client_id}/refresh
  │
  ├─ app/api/v1/summaries.py
  │    validates query params and checks role
  │
  ├─ app/services/clients.py
  │    verifies firm-scoped client access
  │
  ├─ app/services/summaries.py
  │    loads emails, applies date defaults, enforces skip rule
  │
  ├─ app/llm/llm.py or app/llm/gemini.py
  │    calls Gemini or returns mock summary when no key is configured
  │
  ├─ app/utils/utils.py
  │    encrypts summary text
  │
  ├─ app/models/summaries.py
  │    persists EmailSummary and SummarizationLog
  │
  └─ app/cache/cache.py
       invalidates cached summary
```

## Data Ownership

```text
Firm
  ├── Accountant
  └── Client
        ├── Email
        └── EmailSummary

SummarizationLog
  └── tracks each summary generation attempt by client
```

## Requirement Coverage

| Requirement | Implementation |
| --- | --- |
| Persistence layer | `app/models/*`, `app/repositories/*` |
| Optional date range | `refresh_summary()` route and `refresh_client_summary()` service |
| Invalid date rejection | date helper/service validation |
| Partial refresh skip | fewer-than-5-new-emails guard in summary service |
| Gemini resilience | retry/backoff in LLM layer |
| Existing summary preservation | summary record updated only after successful LLM result |
| Authentication | JWT in `app/services/auth.py` |
| Authorization | `require_role()` and firm-scoped client authorization |
| Encrypted summaries | AES-GCM helper in `app/utils/*` |
| Caching | `app/cache/*` |
| Tracking | `SummarizationLog`, `token_in`, `token_out`, `email_count_analyzed` |
| Firm admin report | `/api/v1/summaries/reports/firm-summaries` |
| Superuser report | `/api/v1/summaries/reports/global-summaries` |
| Natural-language search | `/api/v1/summaries/search` |
| Conversation interface | `/api/v1/summaries/conversation` |
