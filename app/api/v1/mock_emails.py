"""Mock Microsoft Graph email capture routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_role
from app.common.schemas import Role
from app.db.database import get_session
from app.models.users import User
from app.schemas.emails import (
    EmailCaptureResponse,
    MockEmailReceiveRequest,
    MockEmailSendRequest,
)
from app.services.emails import mock_receive_email, mock_send_email

router = APIRouter(prefix="/mock-emails", tags=["mock-emails"])


@router.post(
    "/send",
    response_model=EmailCaptureResponse,
    status_code=201,
    summary="Mock Microsoft Graph sendMail",
)
async def create_mock_sent_email(
    request: MockEmailSendRequest,
    current_user: User = Depends(
        require_role(Role.accountant, Role.firm_admin, Role.superuser)
    ),
    session: AsyncSession = Depends(get_session),
) -> EmailCaptureResponse:
    """Insert one outbound mock email and leave summary work queued for the worker."""
    return await mock_send_email(session, current_user=current_user, request=request)


@router.post(
    "/receive",
    response_model=EmailCaptureResponse,
    status_code=201,
    summary="Mock Microsoft Graph received message",
)
async def create_mock_received_email(
    request: MockEmailReceiveRequest,
    current_user: User = Depends(
        require_role(Role.accountant, Role.firm_admin, Role.superuser)
    ),
    session: AsyncSession = Depends(get_session),
) -> EmailCaptureResponse:
    """Insert one inbound mock email and leave summary work queued for the worker."""
    return await mock_receive_email(
        session,
        current_user=current_user,
        request=request,
    )
