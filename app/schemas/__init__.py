"""Data validation schemas (Pydantic layer).

All request/response validation models organized by entity.
Same naming pattern as models/ and api/v1/:
- schemas.auth → AuthRequest, RegisterRequest, UserRead, Token
- schemas.clients → ClientRead
- schemas.emails → EmailRead, MockEmailSendRequest, MockEmailReceiveRequest
- schemas.firms → FirmRead
- schemas.summaries → SummaryQuery, SummaryResult, SummaryResponse
"""
from app.schemas.auth import AuthRequest, RegisterRequest, UserRead, Token
from app.schemas.clients import ClientRead
from app.schemas.emails import (
    EmailRead,
    MockEmailReceiveRequest,
    MockEmailSendRequest,
)
from app.schemas.firms import FirmRead
from app.schemas.summaries import (
    SummaryQuery,
    SummaryResult,
    SummaryResponse,
    ReportFirmClientCount,
    ReportFirmSummaryRow,
    ReportGlobalResponse,
)

__all__ = [
    "AuthRequest",
    "RegisterRequest",
    "UserRead",
    "Token",
    "ClientRead",
    "EmailRead",
    "MockEmailReceiveRequest",
    "MockEmailSendRequest",
    "FirmRead",
    "SummaryQuery",
    "SummaryResult",
    "SummaryResponse",
    "ReportFirmClientCount",
    "ReportFirmSummaryRow",
    "ReportGlobalResponse",
]
