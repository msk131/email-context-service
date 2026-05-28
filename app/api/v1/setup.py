"""Setup and demo data API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import UnauthorizedError
from app.common.schemas import Role
from app.db.database import get_session
from app.models.auth import Accountant
from app.schemas.auth import AuthRequest, RegisterRequest, Token, UserRead
from app.schemas.emails import EmailRead, MockEmailSendRequest, MockThreadRequest, MockThreadResponse
from app.services.auth import (
    authenticate_accountant,
    create_access_token,
    get_optional_current_user,
    register_accountant,
    require_role,
)
from app.services.emails import mock_send_email, mock_send_thread

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=201,
    summary="Register a user account",
    description=(
        "Bootstraps the first superuser when the database has no users. After that, "
        "registration requires a bearer token from a firm admin or superuser. Firm "
        "admins can create users only in their own firm; superusers can create users "
        "for an existing firm_id or a new firm_name."
    ),
    responses={
        201: {"description": "User created"},
        401: {"description": "Authentication required or invalid token"},
        403: {"description": "Current user cannot create the requested role"},
        404: {"description": "Requested firm_id was not found"},
        409: {"description": "Email is already registered"},
        422: {"description": "Invalid role, password, or firm data"},
    },
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
    summary="Login and issue a bearer token",
    description="Authenticates a registered user by email/password and returns a JWT access token.",
    responses={401: {"description": "Invalid email or password"}},
)
async def login(
    request: AuthRequest,
    session: AsyncSession = Depends(get_session),
) -> Token:
    """Login endpoint: authenticate with email and password, return JWT token."""
    user = await authenticate_accountant(session, request.email, request.password)
    if not user:
        raise UnauthorizedError("Invalid email or password")
    
    token_data = {
        "sub": str(user.id),
        "role": user.role.value,
        "firm_id": user.firm_id,
    }
    access_token = create_access_token(token_data)
    return Token(access_token=access_token)


@router.post(
    "/mock-emails",
    response_model=EmailRead,
    status_code=201,
    summary="Insert one mock email",
    description=(
        "Creates a mock inbound or outbound email for an existing client, or creates/reuses "
        "a client when client_name and client_email are provided."
    ),
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access this client"},
        404: {"description": "Client not found"},
        422: {"description": "Invalid request body"},
    },
)
async def create_mock_email(
    request: MockEmailSendRequest,
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> EmailRead:
    """Insert one mock email."""
    return await mock_send_email(session, current_user=current_user, request=request)


@router.post(
    "/mock-email-threads",
    response_model=MockThreadResponse,
    status_code=201,
    summary="Insert a realistic mock email thread",
    description=(
        "Creates a short CPA/client email thread that can immediately be summarized, searched, "
        "or used in conversational Q&A."
    ),
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access this client"},
        404: {"description": "Client not found"},
        422: {"description": "Invalid request body"},
    },
)
async def create_mock_email_thread(
    request: MockThreadRequest,
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> MockThreadResponse:
    """Insert a mock email thread."""
    return await mock_send_thread(session, current_user=current_user, request=request)
