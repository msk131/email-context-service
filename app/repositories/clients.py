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


async def list_clients(
    session: AsyncSession, *, firm_id: int | None = None
) -> list[Client]:
    """List clients, optionally scoped to one firm."""
    statement = select(Client).order_by(Client.name)
    if firm_id is not None:
        statement = statement.where(Client.firm_id == firm_id)
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_client_by_email(
    session: AsyncSession, external_email: str
) -> Client | None:
    """Fetch client by external email address. Returns None if not found."""
    result = await session.execute(
        select(Client).where(Client.external_email == external_email)
    )
    return result.scalar_one_or_none()


async def get_client_by_firm_and_email(
    session: AsyncSession,
    *,
    firm_id: int,
    external_email: str,
) -> Client | None:
    """Fetch client by firm and external email. Returns None if not found."""
    result = await session.execute(
        select(Client).where(
            Client.firm_id == firm_id,
            Client.external_email == external_email,
        )
    )
    return result.scalar_one_or_none()


async def create_client(
    session: AsyncSession,
    *,
    firm_id: int,
    name: str,
    external_email: str,
) -> Client:
    """Create a client."""
    client = Client(firm_id=firm_id, name=name, external_email=external_email)
    session.add(client)
    await session.flush()
    return client


async def update_client(
    session: AsyncSession,
    client: Client,
    *,
    name: str | None = None,
    external_email: str | None = None,
    firm_id: int | None = None,
) -> Client:
    """Update a client."""
    if name is not None:
        client.name = name
    if external_email is not None:
        client.external_email = external_email
    if firm_id is not None:
        client.firm_id = firm_id
    await session.flush()
    return client


async def delete_client(session: AsyncSession, client: Client) -> None:
    """Delete a client."""
    await session.delete(client)
    await session.flush()


async def find_or_create_client(
    session: AsyncSession,
    *,
    firm_id: int,
    name: str,
    external_email: str,
) -> Client:
    """Find client by email, or create if not exists."""
    # Try to find by email
    existing = await get_client_by_email(session, external_email)
    if existing:
        return existing

    # Create new client
    new_client = Client(
        firm_id=firm_id,
        name=name,
        external_email=external_email,
    )
    session.add(new_client)
    await session.flush()
    return new_client
