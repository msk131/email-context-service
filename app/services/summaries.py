"""Compatibility facade for summary-related services."""

from app.services.conversation import answer_email_context_question
from app.services.email_search import search_email_context
from app.services.summary_cache import read_authorized_summary, read_cached_summary
from app.services.summary_refresh import (
    maybe_refresh_summary_for_new_email,
    refresh_client_summary,
)
from app.services.summary_reports import (
    get_firm_summary_report,
    get_global_summary_report,
)
from app.services.summary_tasks import enqueue_summary_refresh_task

__all__ = [
    "answer_email_context_question",
    "enqueue_summary_refresh_task",
    "get_firm_summary_report",
    "get_global_summary_report",
    "maybe_refresh_summary_for_new_email",
    "read_authorized_summary",
    "read_cached_summary",
    "refresh_client_summary",
    "search_email_context",
]
