"""Mock Microsoft Graph email capture routes."""
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_role
from app.common.schemas import Role
from app.db.database import get_session
from app.models.auth import Accountant
from app.schemas.emails import (
    EmailCaptureResponse,
    MockEmailReceiveRequest,
    MockEmailSendRequest,
)
from app.services.emails import mock_receive_email, mock_send_email
from app.tasks.worker import process_task_by_id

router = APIRouter(prefix="/mock-emails", tags=["mock-emails"])


@router.post(
    "/send",
    response_model=EmailCaptureResponse,
    status_code=201,
    summary="Mock Microsoft Graph sendMail",
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
    "/receive",
    response_model=EmailCaptureResponse,
    status_code=201,
    summary="Mock Microsoft Graph received message",
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
