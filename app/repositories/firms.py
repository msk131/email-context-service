"""Firms repository - data access for Firm model."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.firms import Firm
from app.common.exceptions import EntityNotFoundError


async def get_firm_by_id(session: AsyncSession, firm_id: int) -> Firm:
    """Fetch firm by ID. Raises EntityNotFoundError if not found."""
    result = await session.execute(select(Firm).where(Firm.id == firm_id))
    firm = result.scalar_one_or_none()
    if not firm:
        raise EntityNotFoundError("Firm", firm_id)
    return firm
