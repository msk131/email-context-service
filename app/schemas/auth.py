"""Auth domain validation schemas (Pydantic layer)."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.common.schemas import Token, TokenPayload, Role

__all__ = [
    "Token",
    "TokenPayload",
    "Role",
    "AuthRequest",
    "RegisterRequest",
    "UserRead",
]


class AuthRequest(BaseModel):
    """Login request payload."""

    email: EmailStr = Field(..., description="User email address.")
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Plaintext password used only for authentication.",
    )


class RegisterRequest(BaseModel):
    """Create a user account."""

    email: EmailStr = Field(
        ...,
        description="New user's email address.",
        examples=["new.accountant@example.org"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New user's plaintext password.",
        examples=["Password123!"],
    )
    role: Role = Field(
        Role.accountant,
        description="Role assigned to the new user.",
        examples=[Role.accountant],
    )
    firm_id: int | None = Field(
        None, description="Existing firm id for firm-scoped users.", examples=[1]
    )
    firm_name: str | None = Field(
        None,
        min_length=2,
        max_length=255,
        description="Firm name to create or reuse when registering a firm-scoped user.",
        examples=["Ascend Demo CPA"],
    )


class UserRead(BaseModel):
    """User read/response model."""

    id: int
    email: EmailStr
    role: Role
    firm_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
