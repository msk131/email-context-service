"""Task API validation schemas."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SummarizeClientPayload(BaseModel):
    """Payload for a client summary task."""
    client_id: int = Field(..., examples=[42])
    force: bool = Field(False, examples=[True])
    start_date: datetime | None = None
    end_date: datetime | None = None


class TaskCreateRequest(BaseModel):
    """Submit a background task."""
    task_type: Literal["summarize_client"]
    payload: SummarizeClientPayload


class TaskCreateResponse(BaseModel):
    """Accepted task response."""
    task_id: int
    status: str


class TaskStatusResponse(BaseModel):
    """Background task status response."""
    task_id: int
    task_type: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
