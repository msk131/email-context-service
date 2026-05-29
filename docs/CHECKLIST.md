# Email Context Service Checklist

This checklist maps the take-home exercise requirements to the current repository implementation.

## P0 — Must Have
- [x] Firm entity model (`app/models/firms.py`)
- [x] Accountant entity model (`app/models/auth.py`)
- [x] Client entity model (`app/models/clients.py`)
- [x] Email entity model (`app/models/summaries.py`)
- [x] EmailSummary entity model (`app/models/summaries.py`)
- [x] Gemini summarization engine (`app/llm/llm.py`)
- [x] Prompt template/config support (`app/llm/prompts.yml`, `app/llm/prompts.py`)
- [x] Date-range validation and defaults (`app/utils.py`, `app/services/summaries.py`)
- [x] Partial refresh skip when fewer than 5 new emails (`app/services/summaries.py`)
- [x] Retry + exponential backoff for Gemini calls (`app/llm/llm_client.py`)
- [x] Preserve prior summary until new success (service updates only on success)
- [x] Authentication on endpoints (JWT + role-based auth)
- [x] Sensitive summary encryption at rest (`app/utils.py`, `app/services/summaries.py`)
- [x] Summary caching and refresh bypass (`app/cache/`, `app/services/summaries.py`)
- [x] Tracking per client: emails analysed, refreshed timestamp, token usage (`EmailSummary`, `SummarizationLog`)
- [x] Firm admin report of client summaries (`app/api/v1/summaries.py`)
- [x] Superuser global report grouped by firm (`app/api/v1/summaries.py`)

## P1 — Important Enhancements
- [x] Prompt config separated into YAML prompt templates (`app/llm/prompts.yml`)
- [x] Prometheus metrics for LLM usage (`app/llm/llm_client.py`, `app/main.py`)
- [x] DB-backed task queue for heavy APIs (`app/models/tasks.py`, `app/api/v1/tasks.py`, `app/tasks/worker.py`)
- [x] Background worker for long-running summarization tasks
- [x] Existing unit tests for core auth, cache, schemas, LLM, search, and utils
- [x] CI workflow present (`.github/workflows/ci.yml`)
- [x] Conversational email question-answer endpoint exists (`app/api/v1/summaries.py`)
- [ ] Document new task queue, metrics, and prompt configuration flows in README/docs

## P2 — Nice to Have / Future Work
- [ ] Production-scale hardening for 50 firms × 10k clients × 100 emails per client
- [ ] DB performance tuning and index audit
- [ ] Rate limiting and autoscaling readiness
- [ ] Alerting beyond Prometheus scrape metrics
- [ ] Rich conversational multi-turn interface
- [ ] Natural-language search beyond current keyword/context helpers
- [ ] Frontend integration documentation and API examples
- [ ] Task queue pruning, TTL, and worker concurrency controls
- [ ] Expanded queue/worker/metrics unit tests

## Notes
- The repository already includes many required pieces; the remaining work is mostly about production polish, documentation, and stronger load/hardening behavior.
- The current checklist is based on the repository state as of May 29, 2026.
