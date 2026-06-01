"""Repository pattern for data access abstraction.

Repositories encapsulate database queries and provide a clean interface
for services to access data without depending on SQLAlchemy directly.

    Same naming pattern as models/, schemas/, and services/:
- repositories.users → Queries for User
- repositories.clients → Queries for Client
- repositories.emails → Queries for Email
- repositories.email_summaries → Queries for EmailSummary
- repositories.firms → Queries for Firm
"""

from app.repositories.users import get_user_by_email
from app.repositories.clients import count_clients_by_firm, get_client_by_id
from app.repositories.email_summaries import get_summary_record
from app.repositories.emails import list_client_emails
from app.repositories.firms import get_firm_by_id

__all__ = [
    "get_user_by_email",
    "get_client_by_id",
    "count_clients_by_firm",
    "list_client_emails",
    "get_firm_by_id",
    "get_summary_record",
]
