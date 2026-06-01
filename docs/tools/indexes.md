# Indexes And Constraints

## Purpose

Indexes support the hot paths: firm-scoped authorization, client email lookup,
email timeline reads, report refresh decisions, report coverage queries, task
cleanup, and vector retrieval fallback.

## Relational Indexes

| Index / Constraint | Table | Purpose |
| --- | --- | --- |
| `ix_clients_firm_id` | `clients` | Lists and filters clients by firm for authorization and firm dashboards. |
| `uq_clients_firm_external_email` | `clients` | Prevents duplicate client email addresses inside one firm while allowing the same email in another firm if needed. |
| `ix_emails_client_sent_at` | `emails` | Reads a client's email timeline and date-range report inputs in timestamp order. |
| `ix_emails_client_captured_at` | `emails` | Counts newly captured emails since the last report refresh. |
| `ix_emails_subject` | `emails` | Supports lightweight subject lookup and keyword filtering. |
| `ix_emails_sender_address` | `emails` | Supports sender-based lookup and search filtering. |
| `uq_email_summary_client` | `email_summaries` | Enforces one latest generated report row per client. |
| `ix_summarization_logs_client_completed` | `summarization_logs` | Retrieves report-generation audit history by client and completion time. |
| `ix_background_tasks_expires_at` | `background_tasks` | Finds expired terminal tasks for cleanup. |
| `uq_firm_membership_user` | `firm_memberships` | Enforces one active firm membership per non-superuser flow. |
| `uq_firm_membership_user_firm` | `firm_memberships` | Prevents duplicate user-firm membership rows. |
| `uq_accountants_user_firm` | `accountants` | Prevents duplicate accountant profiles for one user in one firm. |

## Vector Indexes

| Index | Table | Purpose |
| --- | --- | --- |
| `ix_email_embeddings_vector` | `email_embeddings` | pgvector `ivfflat` cosine index used when Azure AI Search is unavailable or returns no results. |

The vector index is created only for PostgreSQL. SQLite keeps `email_embeddings`
as JSON so local tests can create the table without pgvector.

## Design Notes

- Composite indexes place the firm/client filter first because almost every
  read path is scoped by ownership before ordering or ranking.
- Unique constraints are part of the domain model, not just performance tuning.
- Report coverage queries aggregate by existing generated-report rows instead
  of scanning raw email bodies.
- Vector retrieval is layered: Azure AI Search first, pgvector second, SQL
  keyword search last.
