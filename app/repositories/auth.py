"""Auth repository - data access for Accountant model."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Accountant


async def get_accountant_by_email(session: AsyncSession, email: str) -> Accountant | None:
    """Fetch accountant by email address."""
    result = await session.execute(select(Accountant).where(Accountant.email == email))
    return result.scalar_one_or_none()


async def get_accountant_by_id(session: AsyncSession, accountant_id: int) -> Accountant | None:
    """Fetch accountant by ID."""
    return await session.get(Accountant, accountant_id)


async def count_accountants(session: AsyncSession) -> int:
    """Count all registered accountant users."""
    result = await session.execute(select(func.count()).select_from(Accountant))
    return int(result.scalar_one())
