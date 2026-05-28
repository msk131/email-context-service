"""Clients domain validation schemas (Pydantic layer)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ClientRead(BaseModel):
    """Client read/response model."""
    id: int
    name: str
    external_email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
