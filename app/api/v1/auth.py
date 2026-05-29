"""Authentication API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_optional_current_user
from app.common.exceptions import UnauthorizedError
from app.db.database import get_session
from app.models.auth import Accountant
from app.schemas.auth import AuthRequest, RegisterRequest, Token, UserRead
from app.services.auth import authenticate_accountant, create_access_token, register_accountant

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=201,
    summary="Register a new user account",
)
async def register(
    request: RegisterRequest,
    current_user: Accountant | None = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Register a new user account."""
    return await register_accountant(
        session,
        email=request.email,
        password=request.password,
        role=request.role,
        firm_id=request.firm_id,
        firm_name=request.firm_name,
        current_user=current_user,
    )


@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate and issue access token",
)
async def login(
    request: AuthRequest,
    session: AsyncSession = Depends(get_session),
) -> Token:
    """Authenticate with email and password, then return a JWT token."""
    user = await authenticate_accountant(session, request.email, request.password)
    if not user:
        raise UnauthorizedError("Invalid email or password")

    token_data = {
        "sub": str(user.id),
        "role": user.role.value,
        "firm_id": user.firm_id,
    }
    return Token(access_token=create_access_token(token_data))
