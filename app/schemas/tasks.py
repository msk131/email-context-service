"""Task API validation schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SummarizeClientPayload(BaseModel):
    """Payload for a client summary task."""

    client_id: int = Field(
        ..., ge=1, description="Client id to summarize.", examples=[42]
    )
    force: bool = Field(
        False,
        description="Force regeneration even when few emails changed.",
        examples=[True],
    )
    start_date: datetime | None = Field(
        None, description="Only summarize emails sent at or after this timestamp."
    )
    end_date: datetime | None = Field(
        None, description="Only summarize emails sent at or before this timestamp."
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_date_range(self) -> "SummarizeClientPayload":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class TaskCreateRequest(BaseModel):
    """Submit a background task."""

    task_type: Literal["summarize_client"] = Field(
        ..., description="Background task type to enqueue."
    )
    payload: SummarizeClientPayload = Field(
        ..., description="Task-specific validated payload."
    )

    model_config = ConfigDict(extra="forbid")


class TaskCreateResponse(BaseModel):
    """Accepted task response."""

    task_id: UUID = Field(..., description="Accepted background task id.")
    status: str = Field(..., description="Current task status.")


class TaskStatusResponse(BaseModel):
    """Background task status response."""

    task_id: UUID = Field(..., description="Background task id.")
    task_type: str = Field(..., description="Background task type.")
    status: str = Field(..., description="Current task status.")
    result: dict[str, Any] | None = Field(
        None, description="Task result when succeeded."
    )
    error: str | None = Field(None, description="Client-safe error code when failed.")
    created_at: datetime = Field(..., description="Task creation timestamp.")
    updated_at: datetime = Field(..., description="Last task update timestamp.")
