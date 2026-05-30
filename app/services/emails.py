"""Microsoft Graph-compatible mock email service."""

from email.utils import make_msgid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.models import EmailDirection
from app.common.schemas import Role
from app.common.time import utc_now
from app.core.logging_config import get_logger
from app.models.auth import Accountant
from app.models.summaries import Email
from app.repositories import tasks as task_repo
from app.repositories.clients import (
    get_client_by_firm_and_email,
    get_client_by_id,
    list_clients_by_email,
)
from app.repositories.emails import list_client_emails
from app.schemas.emails import (
    EmailCaptureResponse,
    EmailRead,
    GraphRecipient,
    MockEmailReceiveRequest,
    MockEmailSendRequest,
)
from app.services.clients import authorize_client_for_user

logger = get_logger("services.emails")


def _mask_email(address: str) -> str:
    local, separator, domain = address.partition("@")
    if not separator:
        return "[redacted]"
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def _recipient_address(recipient: GraphRecipient) -> str:
    return str(recipient.emailAddress.address)


def _recipient_dump(recipient: GraphRecipient) -> dict:
    return recipient.model_dump(mode="json", by_alias=True, exclude_none=True)


def _body_preview(content: str, limit: int = 255) -> str:
    compact = " ".join(content.split())
    return compact[:limit]


def _message_to_email_read(email: Email) -> EmailRead:
    sent_at = email.sent_at
    received_at = email.sent_at if email.direction == EmailDirection.inbound else None
    return EmailRead(
        id=str(email.id),
        createdDateTime=sent_at,
        lastModifiedDateTime=sent_at,
        receivedDateTime=received_at,
        sentDateTime=sent_at,
        hasAttachments=False,
        internetMessageId=make_msgid(idstring=str(email.id)),
        subject=email.subject,
        bodyPreview=_body_preview(email.body_text),
        importance="normal",
        isRead=bool(email.is_read),
        isDraft=False,
        body=email.body,
        sender=email.sender,
        **{"from": email.sender},
        toRecipients=email.to_recipients or [],
        ccRecipients=email.cc_recipients or [],
        bccRecipients=email.bcc_recipients or [],
        replyTo=[],
    )


async def _enqueue_summary_refresh(
    session: AsyncSession, client_id: int, end_date=None
):
    logger.info("Enqueueing summary refresh task for client_id=%s", client_id)
    payload = {"client_id": client_id, "force": False}
    if end_date is not None:
        payload["end_date"] = end_date.isoformat()
    task = await task_repo.create_task(
        session,
        task_type="summarize_client",
        payload=payload,
    )
    logger.info(
        "Summary refresh task enqueued task_id=%s client_id=%s status=%s",
        task.id,
        client_id,
        task.status.value,
    )
    return task


async def _get_client_by_email_for_user(
    session: AsyncSession,
    *,
    current_user: Accountant,
    external_email: str,
):
    role = Role(current_user.role.value)
    if role == Role.superuser:
        matches = await list_clients_by_email(session, external_email, limit=2)
        if len(matches) > 1:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Multiple clients match this email address. Use a firm-scoped "
                    "account or disambiguate the client before capturing this email."
                ),
            )
        client = matches[0] if matches else None
    else:
        client = await get_client_by_firm_and_email(
            session,
            firm_id=current_user.firm_id,
            external_email=external_email,
        )
    if client:
        await authorize_client_for_user(current_user, client, role)
    return client


async def _get_client_for_outbound(
    session: AsyncSession,
    *,
    current_user: Accountant,
    recipients: list[GraphRecipient],
):
    if not recipients:
        raise HTTPException(
            status_code=400,
            detail="At least one toRecipient is required for outbound emails.",
        )
    client_email = _recipient_address(recipients[0])
    logger.info(
        "Resolving outbound email client by recipient=%s", _mask_email(client_email)
    )
    client = await _get_client_by_email_for_user(
        session,
        current_user=current_user,
        external_email=client_email,
    )
    if not client:
        logger.warning(
            "Outbound email capture skipped; client not found email=%s",
            _mask_email(client_email),
        )
        raise HTTPException(
            status_code=404,
            detail=(
                f"Email capture skipped: Client with email '{client_email}' not found. "
                "Please register this client before capturing their emails."
            ),
        )
    return client


async def _get_client_for_inbound(
    session: AsyncSession,
    *,
    current_user: Accountant,
    sender: GraphRecipient,
):
    sender_email = _recipient_address(sender)
    logger.info(
        "Resolving inbound email client by sender=%s", _mask_email(sender_email)
    )
    client = await _get_client_by_email_for_user(
        session,
        current_user=current_user,
        external_email=sender_email,
    )
    if not client:
        logger.warning(
            "Inbound email capture skipped; client not found email=%s",
            _mask_email(sender_email),
        )
        raise HTTPException(
            status_code=404,
            detail=(
                f"Email capture skipped: Client with email '{sender_email}' not found. "
                "Please register this client before capturing their emails."
            ),
        )
    return client


async def mock_send_email(
    session: AsyncSession,
    *,
    current_user: Accountant,
    request: MockEmailSendRequest,
) -> EmailCaptureResponse:
    """
    Insert one outbound mock email from a Microsoft Graph sendMail payload.

    Requires: Client must exist in database for the email address.
    Does not capture emails for non-existent clients.
    """
    message = request.message
    logger.info(
        "Capturing outbound mock email sender=%s recipient_count=%s subject=%r",
        _mask_email(_recipient_address(message.from_)),
        len(message.toRecipients),
        message.subject or "",
    )
    client = await _get_client_for_outbound(
        session,
        current_user=current_user,
        recipients=message.toRecipients,
    )

    email = Email(
        client_id=client.id,
        sender_accountant_id=current_user.id,
        sender=_recipient_dump(message.from_),
        sender_address=_recipient_address(message.from_),
        to_recipients=[_recipient_dump(r) for r in message.toRecipients],
        cc_recipients=[_recipient_dump(r) for r in message.ccRecipients],
        bcc_recipients=[_recipient_dump(r) for r in message.bccRecipients],
        subject=message.subject or "",
        body=message.body.model_dump(mode="json", by_alias=True),
        is_read=bool(message.isRead),
        direction=EmailDirection.outbound,
        sent_at=message.sentDateTime
        or message.receivedDateTime
        or message.createdDateTime,
        captured_at=utc_now(),
    )
    session.add(email)
    task = await _enqueue_summary_refresh(session, client.id, email.sent_at)
    await session.commit()
    await session.refresh(email)
    logger.info(
        "Captured outbound mock email email_id=%s client_id=%s task_id=%s",
        email.id,
        client.id,
        task.id,
    )
    return EmailCaptureResponse(
        message=_message_to_email_read(email),
        summary_task_id=task.id,
        summary_task_status=task.status.value,
    )


async def mock_receive_email(
    session: AsyncSession,
    *,
    current_user: Accountant,
    request: MockEmailReceiveRequest,
) -> EmailCaptureResponse:
    """
    Insert one inbound mock email from a Microsoft Graph message payload.

    Requires: Client must exist in database for the sender address.
    """
    logger.info(
        "Capturing inbound mock email sender=%s recipient_count=%s subject=%r",
        _mask_email(_recipient_address(request.from_)),
        len(request.toRecipients),
        request.subject or "",
    )
    client = await _get_client_for_inbound(
        session,
        current_user=current_user,
        sender=request.from_,
    )
    received_at = (
        request.receivedDateTime or request.sentDateTime or request.createdDateTime
    )

    email = Email(
        client_id=client.id,
        sender_accountant_id=None,
        sender=_recipient_dump(request.from_),
        sender_address=_recipient_address(request.from_),
        to_recipients=[_recipient_dump(r) for r in request.toRecipients],
        cc_recipients=[_recipient_dump(r) for r in request.ccRecipients],
        bcc_recipients=[_recipient_dump(r) for r in request.bccRecipients],
        subject=request.subject or "",
        body=request.body.model_dump(mode="json", by_alias=True),
        is_read=bool(request.isRead),
        direction=EmailDirection.inbound,
        sent_at=received_at,
        captured_at=utc_now(),
    )
    session.add(email)
    task = await _enqueue_summary_refresh(session, client.id, email.sent_at)
    await session.commit()
    await session.refresh(email)
    logger.info(
        "Captured inbound mock email email_id=%s client_id=%s task_id=%s",
        email.id,
        client.id,
        task.id,
    )
    return EmailCaptureResponse(
        message=_message_to_email_read(email),
        summary_task_id=task.id,
        summary_task_status=task.status.value,
    )


async def read_client_emails(
    session: AsyncSession,
    *,
    current_user: Accountant,
    client_id: int,
    limit: int,
) -> list[EmailRead]:
    """Read recent emails for an authorized client."""
    client = await get_client_by_id(session, client_id)
    await authorize_client_for_user(current_user, client, Role(current_user.role.value))
    emails = await list_client_emails(session, client_id, limit)
    return [_message_to_email_read(email) for email in emails]
