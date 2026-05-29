"""Firms domain validation schemas (Pydantic layer)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FirmCreate(BaseModel):
    """Firm create request model."""

    name: str = Field(..., min_length=1, max_length=255)


class FirmUpdate(BaseModel):
    """Firm update request model."""

    name: str = Field(..., min_length=1, max_length=255)


class FirmRead(BaseModel):
    """Firm read/response model."""

    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
