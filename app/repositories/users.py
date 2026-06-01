"""User repository - data access for authenticated users."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User


def _user_load_options():
    return (
        selectinload(User.firm_memberships),
        selectinload(User.accountant_profiles),
    )


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Fetch a user by email address."""
    result = await session.execute(
        select(User).options(*_user_load_options()).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(
    session: AsyncSession, user_id: int
) -> User | None:
    """Fetch a user by ID."""
    result = await session.execute(
        select(User).options(*_user_load_options()).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def count_users(session: AsyncSession) -> int:
    """Count all registered users."""
    result = await session.execute(select(func.count()).select_from(User))
    return int(result.scalar_one())
