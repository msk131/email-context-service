"""Clients domain validation schemas (Pydantic layer)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ClientCreate(BaseModel):
    """Client create request model."""

    name: str = Field(..., min_length=1, max_length=255, description="Client name.")
    external_email: EmailStr = Field(..., description="Client external email address.")
    firm_id: int | None = Field(
        default=None, ge=1, description="Target firm id; required for superusers."
    )


class ClientUpdate(BaseModel):
    """Client update request model."""

    name: str | None = Field(
        default=None, min_length=1, max_length=255, description="Updated client name."
    )
    external_email: EmailStr | None = Field(
        default=None, description="Updated client external email address."
    )
    firm_id: int | None = Field(
        default=None, ge=1, description="Updated firm id; superuser only."
    )


class ClientRead(BaseModel):
    """Client read/response model."""

    id: int
    firm_id: int
    name: str
    external_email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
