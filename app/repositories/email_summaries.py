"""Email summary repository helpers."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.email_summary import EmailSummary
from app.models.firm import Firm


async def get_summary_record(
    session: AsyncSession, client_id: int
) -> EmailSummary | None:
    """Get cached summary record for client, or None if not found."""
    result = await session.execute(
        select(EmailSummary).where(EmailSummary.client_id == client_id)
    )
    return result.scalar_one_or_none()


async def count_summaries_by_firm(session: AsyncSession, firm_id: int) -> int:
    """Count summaries for clients in one firm."""
    result = await session.execute(
        select(func.count(EmailSummary.id))
        .join(Client, EmailSummary.client_id == Client.id)
        .where(Client.firm_id == firm_id)
    )
    return int(result.scalar_one())


async def list_summary_counts_by_firm(
    session: AsyncSession,
) -> list[tuple[int, str, int]]:
    """List summary counts grouped by firm."""
    result = await session.execute(
        select(Firm.id, Firm.name, func.count(EmailSummary.id))
        .join(Client, Client.firm_id == Firm.id)
        .outerjoin(EmailSummary, EmailSummary.client_id == Client.id)
        .group_by(Firm.id, Firm.name)
    )
    return [(firm_id, firm_name, count or 0) for firm_id, firm_name, count in result]
