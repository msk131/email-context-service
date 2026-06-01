"""Clients repository - data access for Client model."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Role
from app.models.client import Client
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


async def count_clients_by_firm(session: AsyncSession, firm_id: int) -> int:
    """Count clients in one firm."""
    result = await session.execute(
        select(func.count(Client.id)).where(Client.firm_id == firm_id)
    )
    return int(result.scalar_one())


async def list_client_inference_candidates(
    session: AsyncSession,
    *,
    role: Role,
    firm_id: int,
    emails: list[str],
    client_ids: list[int],
    name_terms: list[str],
    limit: int = 50,
) -> list[Client]:
    """Return a bounded set of clients that could be referenced in free text."""
    predicates = []
    if emails:
        predicates.append(Client.external_email.in_(emails))
    if client_ids:
        predicates.append(Client.id.in_(client_ids))
    predicates.extend(Client.name.ilike(f"%{term}%") for term in name_terms)

    if not predicates:
        return []

    statement = select(Client)
    if role != Role.superuser:
        statement = statement.where(Client.firm_id == firm_id)
    statement = statement.where(or_(*predicates)).order_by(Client.name).limit(limit)

    result = await session.execute(statement)
    return list(result.scalars().all())


async def list_clients_by_email(
    session: AsyncSession, external_email: str, *, limit: int = 2
) -> list[Client]:
    """Fetch clients by email, bounded so callers can detect ambiguity."""
    result = await session.execute(
        select(Client).where(Client.external_email == external_email).limit(limit)
    )
    return list(result.scalars().all())


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
