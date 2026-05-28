"""Clients repository - data access for Client model."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clients import Client
from app.common.exceptions import EntityNotFoundError


async def get_client_by_id(session: AsyncSession, client_id: int) -> Client:
    """Fetch client by ID. Raises EntityNotFoundError if not found."""
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise EntityNotFoundError("Client", client_id)
    return client
