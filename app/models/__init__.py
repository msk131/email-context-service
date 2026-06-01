"""Database models (ORM layer).

All SQLAlchemy models organized by entity.
Same naming pattern as schemas/ and api/v1/:
- models.users → User, FirmMembership
- models.accountants → Accountant
- models.clients → Client
- models.firms → Firm
- models.summaries → Email, EmailSummary, SummarizationLog
"""

from app.models.accountants import Accountant
from app.models.users import FirmMembership, User
from app.models.clients import Client
from app.models.firms import Firm
from app.models.summaries import Email, EmailSummary, SummarizationLog

__all__ = [
    "User",
    "FirmMembership",
    "Accountant",
    "Client",
    "Firm",
    "Email",
    "EmailSummary",
    "SummarizationLog",
]
