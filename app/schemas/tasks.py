"""Task API validation schemas."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SummarizeClientPayload(BaseModel):
    """Payload for a client summary task."""
    client_id: int = Field(..., ge=1, examples=[42])
    force: bool = Field(False, examples=[True])
    start_date: datetime | None = None
    end_date: datetime | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_date_range(self) -> "SummarizeClientPayload":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class TaskCreateRequest(BaseModel):
    """Submit a background task."""
    task_type: Literal["summarize_client"]
    payload: SummarizeClientPayload

    model_config = ConfigDict(extra="forbid")


class TaskCreateResponse(BaseModel):
    """Accepted task response."""
    task_id: UUID
    status: str


class TaskStatusResponse(BaseModel):
    """Background task status response."""
    task_id: UUID
    task_type: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
