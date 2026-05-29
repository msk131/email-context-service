"""Clients domain validation schemas (Pydantic layer)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ClientCreate(BaseModel):
    """Client create request model."""

    name: str = Field(..., min_length=1, max_length=255)
    external_email: EmailStr
    firm_id: int | None = None


class ClientUpdate(BaseModel):
    """Client update request model."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    external_email: EmailStr | None = None
    firm_id: int | None = None


class ClientRead(BaseModel):
    """Client read/response model."""

    id: int
    firm_id: int
    name: str
    external_email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
