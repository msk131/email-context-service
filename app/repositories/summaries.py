"""Summaries repository - data access for Email, EmailSummary, SummarizationLog models."""

from datetime import datetime

from sqlalchemy import String, cast, func, or_, select
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


async def get_summary_record(
    session: AsyncSession, client_id: int
) -> EmailSummary | None:
    """Get cached summary record for client, or None if not found."""
    result = await session.execute(
        select(EmailSummary).where(EmailSummary.client_id == client_id)
    )
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


async def count_new_emails(
    session: AsyncSession, client_id: int, after: datetime
) -> int:
    """Count emails for client sent after given timestamp."""
    result = await session.execute(
        select(func.count())
        .select_from(Email)
        .where(Email.client_id == client_id)
        .where(Email.sent_at > after)
    )
    return int(result.scalar_one())


async def count_newly_captured_emails(
    session: AsyncSession, client_id: int, after: datetime
) -> int:
    """Count emails captured by the system after a summary refresh timestamp."""
    result = await session.execute(
        select(func.count())
        .select_from(Email)
        .where(Email.client_id == client_id)
        .where(Email.captured_at > after)
    )
    return int(result.scalar_one())


async def count_firm_summaries(session: AsyncSession, firm_id: int) -> int:
    """Count summaries for clients in one firm."""
    result = await session.execute(
        select(func.count(EmailSummary.id))
        .join(Client, EmailSummary.client_id == Client.id)
        .where(Client.firm_id == firm_id)
    )
    return int(result.scalar_one())


async def count_firm_clients(session: AsyncSession, firm_id: int) -> int:
    """Count clients in one firm."""
    result = await session.execute(
        select(func.count(Client.id)).where(Client.firm_id == firm_id)
    )
    return int(result.scalar_one())


async def list_summary_counts_by_firm(
    session: AsyncSession,
) -> list[tuple[int, str, int]]:
    """List summary counts grouped by firm."""
    from app.models.firms import Firm

    result = await session.execute(
        select(Firm.id, Firm.name, func.count(EmailSummary.id))
        .join(Client, Client.firm_id == Firm.id)
        .outerjoin(EmailSummary, EmailSummary.client_id == Client.id)
        .group_by(Firm.id, Firm.name)
    )
    return [(firm_id, firm_name, count or 0) for firm_id, firm_name, count in result]


async def list_accessible_email_summary_rows(
    session: AsyncSession,
    *,
    role: Role,
    firm_id: int,
    client_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[tuple[Email, Client, EmailSummary]]:
    """List accessible email rows with summary embeddings for service ranking."""
    statement = (
        select(Email, Client, EmailSummary)
        .join(Client, Email.client_id == Client.id)
        .join(EmailSummary, Email.client_id == EmailSummary.client_id)
        .where(EmailSummary.embedding.is_not(None))
    )

    if role != Role.superuser:
        statement = statement.where(Client.firm_id == firm_id)
    if client_id is not None:
        statement = statement.where(Email.client_id == client_id)
    if start_date is not None:
        statement = statement.where(Email.sent_at >= start_date)
    if end_date is not None:
        statement = statement.where(Email.sent_at <= end_date)

    result = await session.execute(statement)
    return list(result.all())


async def list_accessible_email_rows(
    session: AsyncSession,
    *,
    role: Role,
    firm_id: int,
    client_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    search_terms: list[str] | None = None,
    limit: int | None = None,
) -> list[tuple[Email, Client]]:
    """List accessible email rows for keyword search using DB-side filtering."""
    statement = select(Email, Client).join(Client, Email.client_id == Client.id)

    if role != Role.superuser:
        statement = statement.where(Client.firm_id == firm_id)
    if client_id is not None:
        statement = statement.where(Email.client_id == client_id)
    if start_date is not None:
        statement = statement.where(Email.sent_at >= start_date)
    if end_date is not None:
        statement = statement.where(Email.sent_at <= end_date)
    if search_terms:
        predicates = []
        searchable_body = cast(Email.body, String)
        for term in search_terms:
            pattern = f"%{term}%"
            predicates.extend(
                [
                    Email.subject.ilike(pattern),
                    searchable_body.ilike(pattern),
                    Email.sender_address.ilike(pattern),
                    Client.name.ilike(pattern),
                    Client.external_email.ilike(pattern),
                ]
            )
        statement = statement.where(or_(*predicates))
    if limit is not None:
        statement = statement.order_by(Email.sent_at.desc()).limit(limit)

    result = await session.execute(statement)
    return list(result.all())
