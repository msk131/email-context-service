"""Mock email send service."""
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import invalidate_summary_cache
from app.common.models import EmailDirection
from app.common.schemas import Role
from app.models.auth import Accountant
from app.models.clients import Client
from app.models.summaries import Email
from app.repositories.clients import get_client_by_id
from app.repositories.emails import get_client_by_external_email, list_client_emails
from app.schemas.emails import EmailRead, MockEmailSendRequest, MockThreadRequest, MockThreadResponse
from app.services.clients import authorize_client_for_user


async def resolve_mock_client(
    session: AsyncSession,
    *,
    current_user: Accountant,
    client_id: int | None,
    client_name: str | None,
    client_email: str | None,
) -> Client:
    """Resolve an existing client or create one for mock email workflows."""
    if client_id is not None:
        client = await get_client_by_id(session, client_id)
        await authorize_client_for_user(current_user, client, current_user.role)
        return client

    if not client_name or not client_email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide client_id or both client_name and client_email",
        )

    firm_id = current_user.firm_id
    client = await get_client_by_external_email(
        session, firm_id=firm_id, external_email=client_email
    )
    if client:
        return client

    client = Client(firm_id=firm_id, name=client_name, external_email=client_email)
    session.add(client)
    await session.flush()
    return client


async def mock_send_email(
    session: AsyncSession,
    *,
    current_user: Accountant,
    request: MockEmailSendRequest,
) -> EmailRead:
    """Insert one mock email for an authorized client."""
    client = await resolve_mock_client(
        session,
        current_user=current_user,
        client_id=request.client_id,
        client_name=request.client_name,
        client_email=str(request.client_email) if request.client_email else None,
    )

    if request.direction == EmailDirection.outbound:
        sender_email = str(request.sender_email or current_user.email)
        recipients = [str(value) for value in (request.recipients or [client.external_email])]
        sender_accountant_id = current_user.id
    else:
        sender_email = str(request.sender_email or client.external_email)
        recipients = [str(value) for value in (request.recipients or [current_user.email])]
        sender_accountant_id = None

    email = Email(
        client_id=client.id,
        sender_accountant_id=sender_accountant_id,
        sender_email=sender_email,
        recipients=recipients,
        subject=request.subject,
        body=request.body,
        direction=request.direction,
        sent_at=request.sent_at or datetime.now(),
    )
    session.add(email)
    await session.commit()
    await session.refresh(email)
    await invalidate_summary_cache(client.id)
    return EmailRead.model_validate(email)


async def mock_send_thread(
    session: AsyncSession,
    *,
    current_user: Accountant,
    request: MockThreadRequest,
) -> MockThreadResponse:
    """Insert a realistic CPA email thread for demo/testing."""
    client = await resolve_mock_client(
        session,
        current_user=current_user,
        client_id=request.client_id,
        client_name=request.client_name,
        client_email=str(request.client_email) if request.client_email else None,
    )
    now = datetime.now()
    templates = [
        (
            EmailDirection.outbound,
            "Tax return kickoff and document checklist",
            "Please send W-2s, 1099-INT, 1099-DIV, mortgage interest, and charitable donation receipts.",
        ),
        (
            EmailDirection.inbound,
            "Re: Tax return kickoff and document checklist",
            "I uploaded my W-2 and mortgage interest. I am still waiting for the 1099-INT from First Bank.",
        ),
        (
            EmailDirection.outbound,
            f"{request.topic} follow-up",
            "Thanks. The only blocker is the missing 1099-INT. Please send it when First Bank makes it available.",
        ),
        (
            EmailDirection.inbound,
            "Estimated payment question",
            "Can you confirm whether my Q4 estimated payment was applied? I paid it on January 12.",
        ),
        (
            EmailDirection.outbound,
            "Estimated payment confirmed",
            "Confirmed: the Q4 estimated payment is reflected. We still need the 1099-INT before final review.",
        ),
        (
            EmailDirection.inbound,
            "1099-INT received",
            "I received the 1099-INT and attached it. Please let me know if anything else is missing.",
        ),
    ]

    emails = []
    for index in range(request.message_count):
        direction, subject, body = templates[index % len(templates)]
        if direction == EmailDirection.outbound:
            sender_email = current_user.email
            recipients = [client.external_email]
            sender_accountant_id = current_user.id
        else:
            sender_email = client.external_email
            recipients = [current_user.email]
            sender_accountant_id = None
        emails.append(
            Email(
                client_id=client.id,
                sender_accountant_id=sender_accountant_id,
                sender_email=sender_email,
                recipients=recipients,
                subject=subject,
                body=body,
                direction=direction,
                sent_at=now - timedelta(days=request.message_count - index),
            )
        )

    session.add_all(emails)
    await session.commit()
    for email in emails:
        await session.refresh(email)
    await invalidate_summary_cache(client.id)
    return MockThreadResponse(
        client_id=client.id,
        inserted_count=len(emails),
        emails=[EmailRead.model_validate(email) for email in emails],
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
    return [EmailRead.model_validate(email) for email in emails]
