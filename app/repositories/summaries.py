"""Summaries repository - data access for Email, EmailSummary, SummarizationLog models."""
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.summaries import Email, EmailSummary
from app.models.clients import Client
from app.common.schemas import Role
from app.common.exceptions import EntityNotFoundError


async def load_client(session: AsyncSession, client_id: int) -> Client:
    """Load client by ID. Raises EntityNotFoundError if not found."""
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise EntityNotFoundError("Client", client_id)
    return client


async def get_summary_record(session: AsyncSession, client_id: int) -> Optional[EmailSummary]:
    """Get cached summary record for client, or None if not found."""
    result = await session.execute(select(EmailSummary).where(EmailSummary.client_id == client_id))
    return result.scalar_one_or_none()


async def get_emails(
    session: AsyncSession, client_id: int, start_date: datetime, end_date: datetime
) -> list[Email]:
    """Get emails for client within date range, ordered by sent_at."""
    result = await session.execute(
        select(Email)
        .where(Email.client_id == client_id)
        .where(Email.sent_at >= start_date)
        .where(Email.sent_at <= end_date)
        .order_by(Email.sent_at.asc())
    )
    return result.scalars().all()


async def count_new_emails(session: AsyncSession, client_id: int, after: datetime) -> int:
    """Count emails for client sent after given timestamp."""
    result = await session.execute(
        select(func.count())
        .select_from(Email)
        .where(Email.client_id == client_id)
        .where(Email.sent_at > after)
    )
    return int(result.scalar_one())


async def search_accessible_emails(
    session: AsyncSession,
    *,
    query: str,
    role: Role,
    firm_id: int,
    client_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 25,
) -> list[tuple[Email, Client]]:
    """Search emails the current user can access."""
    terms = [term.lower() for term in query.split() if len(term.strip()) > 1]
    filters = []
    for term in terms:
        pattern = f"%{term}%"
        filters.append(
            or_(
                func.lower(Email.subject).like(pattern),
                func.lower(Email.body).like(pattern),
                func.lower(Email.sender_email).like(pattern),
                func.lower(Client.name).like(pattern),
                func.lower(Client.external_email).like(pattern),
            )
        )

    statement = select(Email, Client).join(Client, Email.client_id == Client.id)
    if filters:
        statement = statement.where(or_(*filters))
    if role != Role.superuser:
        statement = statement.where(Client.firm_id == firm_id)
    if client_id is not None:
        statement = statement.where(Email.client_id == client_id)
    if start_date is not None:
        statement = statement.where(Email.sent_at >= start_date)
    if end_date is not None:
        statement = statement.where(Email.sent_at <= end_date)

    result = await session.execute(statement.order_by(Email.sent_at.desc()).limit(limit))
    return list(result.all())
