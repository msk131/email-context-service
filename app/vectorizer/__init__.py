"""Vector search and retrieval adapters."""

from app.vectorizer.retrievers import RetrievalDocument, retrieve_email_context

__all__ = ["RetrievalDocument", "retrieve_email_context"]
