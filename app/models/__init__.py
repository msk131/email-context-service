"""Database models (ORM layer).

All SQLAlchemy models organized by entity.
Same naming pattern as schemas/ and api/v1/:
- models.auth → Accountant, etc.
- models.clients → Client
- models.firms → Firm
- models.summaries → Email, EmailSummary, SummarizationLog
"""

from app.models.auth import Accountant
from app.models.clients import Client
from app.models.firms import Firm
from app.models.summaries import Email, EmailSummary, SummarizationLog

__all__ = [
    "Accountant",
    "Client",
    "Firm",
    "Email",
    "EmailSummary",
    "SummarizationLog",
]
