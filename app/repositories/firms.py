"""Firms repository - data access for Firm model."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.firm import Firm
from app.common.exceptions import EntityNotFoundError


async def get_firm_by_id(session: AsyncSession, firm_id: int) -> Firm:
    """Fetch firm by ID. Raises EntityNotFoundError if not found."""
    result = await session.execute(select(Firm).where(Firm.id == firm_id))
    firm = result.scalar_one_or_none()
    if not firm:
        raise EntityNotFoundError("Firm", firm_id)
    return firm


async def get_firm_by_name(session: AsyncSession, name: str) -> Firm | None:
    """Fetch firm by name. Returns None when not found."""
    result = await session.execute(select(Firm).where(Firm.name == name))
    return result.scalar_one_or_none()


async def list_firms(session: AsyncSession) -> list[Firm]:
    """List all firms."""
    result = await session.execute(select(Firm).order_by(Firm.name))
    return list(result.scalars().all())


async def create_firm(session: AsyncSession, *, name: str) -> Firm:
    """Create a firm."""
    firm = Firm(name=name)
    session.add(firm)
    await session.flush()
    return firm


async def update_firm(session: AsyncSession, firm: Firm, *, name: str) -> Firm:
    """Update a firm."""
    firm.name = name
    await session.flush()
    return firm


async def delete_firm(session: AsyncSession, firm: Firm) -> None:
    """Delete a firm."""
    await session.delete(firm)
    await session.flush()
