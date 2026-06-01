"""Summaries domain validation schemas (Pydantic layer)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class SummaryQuery(BaseModel):
    """Query parameters for summary endpoint."""

    start_date: datetime | None = Field(
        None, description="Only include emails sent at or after this timestamp."
    )
    end_date: datetime | None = Field(
        None, description="Only include emails sent at or before this timestamp."
    )


class SummaryResult(BaseModel):
    """Summary result data model."""

    summary: str = Field(
        ...,
        examples=["Client provided W-2s and still needs to send brokerage statements."],
    )
    actors: list[str] = Field(
        default_factory=list, examples=[["client@example.com", "sara@example.org"]]
    )
    concluded_discussions: list[str] = Field(
        default_factory=list, examples=[["Confirmed filing extension."]]
    )
    open_action_items: list[str] = Field(
        default_factory=list, examples=[["Client to send 1099-INT."]]
    )
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
    reason: str | None = Field(
        None, examples=["Fewer than 5 new emails have arrived since last refresh"]
    )
    result: SummaryResult | None = None


class SummaryRefreshTaskResponse(BaseModel):
    """Accepted background summary refresh task."""

    task_id: UUID = Field(..., examples=["4c6155a5-7f5c-4a7d-93fa-41b01dbf4952"])
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

    summaries_by_firm: list[ReportFirmSummaryRow] = Field(default_factory=list)
    total_firms: int = Field(..., ge=0, examples=[12])
    total_clients_with_summaries: int = Field(..., ge=0, examples=[156])
    generated_at: datetime


class EmailSearchMatch(BaseModel):
    """Search result for one email."""

    id: int = Field(..., examples=[9001])
    client_id: int = Field(..., examples=[101])
    client_name: str = Field(..., examples=["Akshar Patel"])
    sender_email: str = Field(..., examples=["akshar@example.com"])
    recipients: list[str] = Field(default_factory=list, examples=[["sara@example.org"]])
    subject: str = Field(..., max_length=512, examples=["1099-INT follow-up"])
    snippet: str = Field(
        ...,
        max_length=500,
        examples=["The 1099-INT from First Bank is still missing..."],
    )
    sent_at: datetime
    relevance_score: int = Field(..., ge=1, examples=[3])

    model_config = ConfigDict(from_attributes=True)


class EmailSearchResponse(BaseModel):
    """Natural language email search response."""

    query: str = Field(
        ..., min_length=2, max_length=256, examples=["clients missing 1099-INT"]
    )
    total: int = Field(..., ge=0, examples=[4])
    results: list[EmailSearchMatch] = Field(default_factory=list)
