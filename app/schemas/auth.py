"""Auth domain validation schemas (Pydantic layer)."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.common.schemas import Token, TokenPayload, Role

__all__ = ["Token", "TokenPayload", "Role", "AuthRequest", "RegisterRequest", "UserRead"]


class AuthRequest(BaseModel):
    """Login request payload."""
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    """Create a user account."""
    email: EmailStr = Field(..., examples=["new.accountant@example.org"])
    password: str = Field(..., min_length=8, max_length=128, examples=["Password123!"])
    role: Role = Field(Role.accountant, examples=[Role.accountant])
    firm_id: Optional[int] = Field(None, examples=[1])
    firm_name: Optional[str] = Field(None, min_length=2, max_length=255, examples=["Ascend Demo CPA"])


class UserRead(BaseModel):
    """User read/response model."""
    id: int
    email: EmailStr
    role: Role
    firm_id: int

    model_config = ConfigDict(from_attributes=True)
