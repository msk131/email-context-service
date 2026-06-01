"""Firms service - business logic for firm operations."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import AccessDeniedError
from app.common.schemas import Role
from app.models.users import User
from app.models.firms import Firm
from app.repositories.firms import (
    create_firm,
    delete_firm,
    get_firm_by_id,
    get_firm_by_name,
    list_firms,
    update_firm,
)


def _role(user: User) -> Role:
    """Return the API role enum for an accountant."""
    return Role(user.role.value)


def _authorize_firm_access(user: User, firm_id: int) -> None:
    """Allow superusers to access any firm and other users only their own firm."""
    if _role(user) == Role.superuser:
        return
    if user.firm_id != firm_id:
        raise AccessDeniedError("Access denied for this firm")


async def get_firm_service(session: AsyncSession, firm_id: int) -> Firm:
    """Business logic: Get firm details."""
    return await get_firm_by_id(session, firm_id)


async def list_firms_service(
    session: AsyncSession, current_user: User
) -> list[Firm]:
    """List firms visible to the current user."""
    if _role(current_user) == Role.superuser:
        return await list_firms(session)
    return [await get_firm_by_id(session, current_user.firm_id)]


async def get_authorized_firm_service(
    session: AsyncSession,
    *,
    firm_id: int,
    current_user: User,
) -> Firm:
    """Get a firm after enforcing firm-scoped access."""
    firm = await get_firm_by_id(session, firm_id)
    _authorize_firm_access(current_user, firm.id)
    return firm


async def create_firm_service(session: AsyncSession, *, name: str) -> Firm:
    """Create a firm, rejecting duplicate names before hitting the DB."""
    existing = await get_firm_by_name(session, name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A firm with this name already exists",
        )
    firm = await create_firm(session, name=name)
    await session.commit()
    await session.refresh(firm)
    return firm


async def update_firm_service(
    session: AsyncSession,
    *,
    firm_id: int,
    name: str,
    current_user: User,
) -> Firm:
    """Update a firm if the user can manage it."""
    firm = await get_firm_by_id(session, firm_id)
    _authorize_firm_access(current_user, firm.id)

    existing = await get_firm_by_name(session, name)
    if existing and existing.id != firm.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A firm with this name already exists",
        )
    firm = await update_firm(session, firm, name=name)
    await session.commit()
    await session.refresh(firm)
    return firm


async def delete_firm_service(session: AsyncSession, *, firm_id: int) -> None:
    """Delete a firm."""
    firm = await get_firm_by_id(session, firm_id)
    await delete_firm(session, firm)
    await session.commit()
