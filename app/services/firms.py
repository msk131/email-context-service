"""Firms service - business logic for firm operations."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.firms import get_firm_by_id
from app.models.firms import Firm


async def get_firm_service(session: AsyncSession, firm_id: int) -> Firm:
    """Business logic: Get firm details."""
    return await get_firm_by_id(session, firm_id)
