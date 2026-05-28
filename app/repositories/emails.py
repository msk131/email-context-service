"""Email repository helpers."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clients import Client
from app.models.summaries import Email


async def get_client_by_external_email(
    session: AsyncSession, *, firm_id: int, external_email: str
) -> Client | None:
    """Find a client in a firm by external email."""
    result = await session.execute(
        select(Client).where(Client.firm_id == firm_id, Client.external_email == external_email)
    )
    return result.scalar_one_or_none()


async def list_client_emails(session: AsyncSession, client_id: int, limit: int = 50) -> list[Email]:
    """List recent client emails."""
    result = await session.execute(
        select(Email)
        .where(Email.client_id == client_id)
        .order_by(Email.sent_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
