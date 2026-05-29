"""Setup and demo data API routes."""
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import UnauthorizedError
from app.common.schemas import Role
from app.db.database import get_session
from app.models.auth import Accountant
from app.schemas.auth import AuthRequest, RegisterRequest, Token, UserRead
from app.schemas.emails import (
    EmailCaptureResponse,
    MockEmailReceiveRequest,
    MockEmailSendRequest,
)
from app.tasks.worker import process_task_by_id
from app.api.dependencies.auth import get_optional_current_user, require_role
from app.services.auth import (
    authenticate_accountant,
    create_access_token,
    register_accountant,
)
from app.services.emails import mock_receive_email, mock_send_email

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=201,
    summary="Register a new user account",
    description=(
        "Creates a new user account. Bootstraps the first superuser when no users exist. "
        "Subsequent registrations require an authenticated firm admin or superuser."
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
    summary="Authenticate and issue access token",
    description="Validates a registered user's credentials and returns a JWT bearer token for API access.",
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
    "/mock-emails/send",
    response_model=EmailCaptureResponse,
    status_code=201,
    summary="Mock Microsoft Graph sendMail",
    description=(
        "Stores an outbound email from a Microsoft Graph sendMail JSON body. "
        "All standard Graph message fields are optional except the capture fields: "
        "sender/from, toRecipients, one timestamp, and body.content. Mock examples "
        "show only the required fields to keep testing payloads small."
    ),
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access this client"},
        404: {"description": "Client not found"},
        422: {"description": "Invalid request body"},
    },
)
async def create_mock_sent_email(
    http_request: Request,
    request: MockEmailSendRequest,
    background_tasks: BackgroundTasks,
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> EmailCaptureResponse:
    """Insert one outbound mock email from a Graph sendMail payload."""
    response = await mock_send_email(session, current_user=current_user, request=request)
    background_tasks.add_task(
        process_task_by_id,
        response.summary_task_id,
        getattr(http_request.state, "request_id", None),
    )
    return response


@router.post(
    "/mock-emails/receive",
    response_model=EmailCaptureResponse,
    status_code=201,
    summary="Mock Microsoft Graph received message",
    description=(
        "Stores an inbound email from a Microsoft Graph message JSON shape. "
        "All standard Graph fields are optional except sender/from, at least one "
        "recipient, one timestamp, and body.content. Mock examples show only the "
        "required fields to keep testing payloads small."
    ),
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access this client"},
        404: {"description": "Client not found"},
        422: {"description": "Invalid request body"},
    },
)
async def create_mock_received_email(
    http_request: Request,
    request: MockEmailReceiveRequest,
    background_tasks: BackgroundTasks,
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> EmailCaptureResponse:
    """Insert one inbound mock email from a Graph message payload."""
    response = await mock_receive_email(
        session,
        current_user=current_user,
        request=request,
    )
    background_tasks.add_task(
        process_task_by_id,
        response.summary_task_id,
        getattr(http_request.state, "request_id", None),
    )
    return response
