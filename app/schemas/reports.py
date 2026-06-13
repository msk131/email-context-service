"""Report read-model schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ReportFirmClientCount(BaseModel):
    """Firm report coverage: count of clients with generated reports."""

    client_count_with_summaries: int = Field(..., ge=0, examples=[38])
    total_clients_in_firm: int = Field(..., ge=0, examples=[45])
    coverage_percentage: float = Field(..., ge=0, le=100, examples=[84.4])
    generated_at: datetime


class ReportFirmSummaryRow(BaseModel):
    """Row in global client-report coverage."""

    firm_id: int = Field(..., examples=[7])
    firm_name: str = Field(..., examples=["Ascend CPA North"])
    client_count_with_summaries: int = Field(..., ge=0, examples=[38])


class ReportGlobalResponse(BaseModel):
    """Global client-report coverage response."""

    summaries_by_firm: list[ReportFirmSummaryRow] = Field(default_factory=list)
    total_firms: int = Field(..., ge=0, examples=[12])
    total_clients_with_summaries: int = Field(..., ge=0, examples=[156])
    generated_at: datetime
