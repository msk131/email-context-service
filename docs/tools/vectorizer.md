# Vectorizer

## Tools

- Azure AI Search
- pgvector
- Local deterministic embeddings fallback

## Purpose

The vectorizer retrieves relevant email context for search and conversation.
Azure AI Search is the production primary retriever. pgvector is the open-source
fallback. SQL keyword search remains the final fallback for local development
and empty vector results.

## Where It Lives

- Retrieval providers: `app/vectorizer/retrievers.py`
- Search orchestration: `app/services/email_search.py`
- Embeddings: `app/llm/embeddings.py`
- Email embedding persistence: `app/repositories/emails.py`, `app/models/email_embedding.py`

## Design Notes

- `VECTORIZER_ENABLED` controls vector retrieval.
- Azure settings use `AZURE_AI_SEARCH_*` environment variables.
- pgvector fallback reads from `email_embeddings`.
- Search results are firm-scoped before reaching API responses.
