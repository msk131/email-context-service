"""Repository pattern for data access abstraction.

Repositories encapsulate database queries and provide a clean interface
for services to access data without depending on SQLAlchemy directly.

Same naming pattern as models/, schemas/, and services/:
- repositories.auth → Queries for Accountant
- repositories.clients → Queries for Client
- repositories.firms → Queries for Firm
- repositories.summaries → Queries for Email, EmailSummary, SummarizationLog
"""
from app.repositories.auth import get_accountant_by_email
from app.repositories.clients import get_client_by_id
from app.repositories.emails import get_client_by_external_email, list_client_emails
from app.repositories.firms import get_firm_by_id
from app.repositories.summaries import (
    get_summary_record,
    get_emails,
    count_new_emails,
    count_newly_captured_emails,
    load_client,
)

__all__ = [
    "get_accountant_by_email",
    "get_client_by_id",
    "get_client_by_external_email",
    "list_client_emails",
    "get_firm_by_id",
    "get_summary_record",
    "get_emails",
    "count_new_emails",
    "count_newly_captured_emails",
    "load_client",
]
