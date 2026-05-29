"""Summaries domain validation schemas (Pydantic layer)."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class SummaryQuery(BaseModel):
    """Query parameters for summary endpoint."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SummaryResult(BaseModel):
    """Summary result data model."""
    summary: str = Field(..., examples=["Client provided W-2s and still needs to send brokerage statements."])
    actors: List[str] = Field(default_factory=list, examples=[["client@example.com", "sara@example.org"]])
    concluded_discussions: List[str] = Field(default_factory=list, examples=[["Confirmed filing extension."]])
    open_action_items: List[str] = Field(default_factory=list, examples=[["Client to send 1099-INT."]])
    email_count_analyzed: int = Field(..., ge=0, examples=[12])
    refreshed_at: datetime
    token_in: int = Field(..., ge=0, examples=[1420])
    token_out: int = Field(..., ge=0, examples=[280])


class SummaryResponse(BaseModel):
    """Summary API response model."""
    client_id: int = Field(..., examples=[101])
    client_name: str = Field(..., examples=["Akshar Patel"])
    firm_id: int = Field(..., examples=[7])
    refreshed_at: datetime
    skipped: bool = Field(False, examples=[False])
    reason: Optional[str] = Field(None, examples=["Fewer than 5 new emails have arrived since last refresh"])
    result: Optional[SummaryResult] = None


class SummaryRefreshTaskResponse(BaseModel):
    """Accepted background summary refresh task."""
    task_id: int = Field(..., examples=[42])
    status: str = Field(..., examples=["pending"])


class ReportFirmClientCount(BaseModel):
    """Firm summary report (count of clients with summaries)."""
    client_count_with_summaries: int = Field(..., ge=0, examples=[38])
    total_clients_in_firm: int = Field(..., ge=0, examples=[45])
    coverage_percentage: float = Field(..., ge=0, le=100, examples=[84.4])
    generated_at: datetime


class ReportFirmSummaryRow(BaseModel):
    """Row in global summary report."""
    firm_id: int = Field(..., examples=[7])
    firm_name: str = Field(..., examples=["Ascend CPA North"])
    client_count_with_summaries: int = Field(..., ge=0, examples=[38])


class ReportGlobalResponse(BaseModel):
    """Global summary report (all firms)."""
    summaries_by_firm: List[ReportFirmSummaryRow] = Field(default_factory=list)
    total_firms: int = Field(..., ge=0, examples=[12])
    total_clients_with_summaries: int = Field(..., ge=0, examples=[156])
    generated_at: datetime


class EmailSearchMatch(BaseModel):
    """Search result for one email."""
    id: int = Field(..., examples=[9001])
    client_id: int = Field(..., examples=[101])
    client_name: str = Field(..., examples=["Akshar Patel"])
    sender_email: str = Field(..., examples=["akshar@example.com"])
    recipients: List[str] = Field(default_factory=list, examples=[["sara@example.org"]])
    subject: str = Field(..., examples=["1099-INT follow-up"])
    snippet: str = Field(..., examples=["The 1099-INT from First Bank is still missing..."])
    sent_at: datetime
    relevance_score: int = Field(..., ge=1, examples=[3])

    model_config = ConfigDict(from_attributes=True)


class EmailSearchResponse(BaseModel):
    """Natural language email search response."""
    query: str = Field(..., min_length=2, examples=["clients missing 1099-INT"])
    total: int = Field(..., ge=0, examples=[4])
    results: List[EmailSearchMatch] = Field(default_factory=list)


class ConversationRequest(BaseModel):
    """Question-answer request over accessible email context."""
    question: str = Field(
        ...,
        min_length=3,
        examples=["What is still blocking Akshar's tax return?"],
    )

    model_config = ConfigDict(extra="forbid")


class ConversationResponse(BaseModel):
    """Conversational answer grounded in matched emails."""
    question: str = Field(..., examples=["What is still blocking Akshar's tax return?"])
    answer: str = Field(..., examples=["The main blocker is the missing 1099-INT."])
    source_email_count: int = Field(..., ge=0, examples=[3])
    sources: List[EmailSearchMatch] = Field(default_factory=list)
