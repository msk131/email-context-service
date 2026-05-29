"""Clients service - business logic for client operations."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Accountant
from app.models.clients import Client
from app.repositories.clients import (
    create_client,
    delete_client,
    get_client_by_firm_and_email,
    get_client_by_id,
    list_clients,
    update_client,
)
from app.repositories.firms import get_firm_by_id
from app.common.exceptions import AccessDeniedError
from app.common.schemas import Role


def _role(user: Accountant) -> Role:
    """Return the API role enum for an accountant."""
    return Role(user.role.value)


async def authorize_client_for_user(
    user: Accountant, client: Client, role: Role
) -> None:
    """Authorize user access to client (must be same firm or superuser).

    Raises AccessDeniedError if user cannot access this client.
    """
    if Role(role.value if hasattr(role, "value") else role) == Role.superuser:
        return
    if client.firm_id != user.firm_id:
        raise AccessDeniedError("Access denied for this client")


def resolve_client_firm_id(
    current_user: Accountant, requested_firm_id: int | None
) -> int:
    """Resolve and authorize the target firm for client writes."""
    if _role(current_user) == Role.superuser:
        if requested_firm_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="firm_id is required for superusers",
            )
        return requested_firm_id
    if requested_firm_id is not None and requested_firm_id != current_user.firm_id:
        raise AccessDeniedError("Cannot manage clients for another firm")
    return current_user.firm_id


async def list_clients_service(
    session: AsyncSession,
    *,
    current_user: Accountant,
    firm_id: int | None = None,
) -> list[Client]:
    """List clients visible to the current user."""
    if _role(current_user) == Role.superuser:
        return await list_clients(session, firm_id=firm_id)
    if firm_id is not None and firm_id != current_user.firm_id:
        raise AccessDeniedError("Cannot list clients for another firm")
    return await list_clients(session, firm_id=current_user.firm_id)


async def get_client_service(
    session: AsyncSession,
    *,
    client_id: int,
    current_user: Accountant,
) -> Client:
    """Get a client after enforcing firm-scoped access."""
    client = await get_client_by_id(session, client_id)
    await authorize_client_for_user(current_user, client, _role(current_user))
    return client


async def create_client_service(
    session: AsyncSession,
    *,
    name: str,
    external_email: str,
    firm_id: int | None,
    current_user: Accountant,
) -> Client:
    """Create a client in an authorized firm."""
    target_firm_id = resolve_client_firm_id(current_user, firm_id)
    await get_firm_by_id(session, target_firm_id)

    existing = await get_client_by_firm_and_email(
        session,
        firm_id=target_firm_id,
        external_email=external_email,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A client with this email already exists for this firm",
        )
    client = await create_client(
        session,
        firm_id=target_firm_id,
        name=name,
        external_email=external_email,
    )
    await session.commit()
    await session.refresh(client)
    return client


async def update_client_service(
    session: AsyncSession,
    *,
    client_id: int,
    name: str | None,
    external_email: str | None,
    firm_id: int | None,
    current_user: Accountant,
) -> Client:
    """Update a client after enforcing firm-scoped access."""
    client = await get_client_by_id(session, client_id)
    await authorize_client_for_user(current_user, client, _role(current_user))

    target_firm_id = None
    if firm_id is not None:
        target_firm_id = resolve_client_firm_id(current_user, firm_id)
        await get_firm_by_id(session, target_firm_id)

    final_firm_id = target_firm_id if target_firm_id is not None else client.firm_id
    final_email = (
        external_email if external_email is not None else client.external_email
    )
    existing = await get_client_by_firm_and_email(
        session,
        firm_id=final_firm_id,
        external_email=final_email,
    )
    if existing and existing.id != client.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A client with this email already exists for this firm",
        )

    client = await update_client(
        session,
        client,
        name=name,
        external_email=external_email,
        firm_id=target_firm_id,
    )
    await session.commit()
    await session.refresh(client)
    return client


async def delete_client_service(
    session: AsyncSession,
    *,
    client_id: int,
    current_user: Accountant,
) -> None:
    """Delete a client after enforcing firm-scoped access."""
    client = await get_client_by_id(session, client_id)
    await authorize_client_for_user(current_user, client, _role(current_user))
    await delete_client(session, client)
    await session.commit()
