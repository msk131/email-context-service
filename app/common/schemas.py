"""Shared Pydantic schemas."""
from enum import Enum

from pydantic import BaseModel
from typing import Optional, Dict, Any


class Role(str, Enum):
    """Role enumeration for API contracts."""
    superuser = "superuser"
    firm_admin = "firm_admin"
    accountant = "accountant"


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str
    role: Role
    firm_id: int
    exp: int


class ErrorDetail(BaseModel):
    """Standard error detail envelope for API responses."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""
    error: ErrorDetail
