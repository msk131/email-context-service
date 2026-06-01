# AI And Report Generation

## Tools

- LLM provider adapter
- YAML prompt templates
- `httpx`
- Local mock mode
- Embedding helper

## Purpose

The AI layer generates structured client reports from authorized email context.
It also creates embeddings used by vector retrieval.

## Where It Lives

- LLM adapter: `app/llm/service.py`
- Prompt templates: `app/llm/prompts.yml`
- Prompt renderer: `app/llm/prompts.py`
- Embeddings: `app/llm/embeddings.py`
- Report generation service: `app/services/summaries.py`

## Design Notes

- Prompts explicitly treat email bodies as untrusted evidence.
- Provider calls use async HTTP and retry/backoff.
- Token usage is recorded for cost visibility.
- Missing API keys trigger mock mode for local tests and demos.
