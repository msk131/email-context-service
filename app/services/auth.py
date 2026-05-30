"""Auth service - business logic for authentication."""

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
import bcrypt
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.setting import settings
from app.models.auth import Accountant
from app.models.firms import Firm
from app.repositories.auth import count_accountants, get_accountant_by_email
from app.common.models import RoleEnum
from app.common.schemas import Role

BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password cannot be longer than 72 bytes",
        )
    return password_bytes


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > BCRYPT_MAX_BYTES:
            return False
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except ValueError:
        return False


async def hash_password_async(password: str) -> str:
    """Hash a password without blocking the event loop."""
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(password: str, password_hash: str) -> bool:
    """Verify a password without blocking the event loop."""
    return await asyncio.to_thread(verify_password, password, password_hash)


async def authenticate_accountant(
    session: AsyncSession, email: str, password: str
) -> Accountant | None:
    """Authenticate accountant with email and password. Returns None if invalid."""
    user = await get_accountant_by_email(session, email)
    if not user:
        return None
    if not await verify_password_async(password, user.password_hash):
        return None
    return user


async def register_accountant(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    role: Role,
    firm_id: int | None = None,
    firm_name: str | None = None,
    current_user: Accountant | None = None,
) -> Accountant:
    """Register a user with bootstrap and admin-only rules."""
    existing = await get_accountant_by_email(session, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user_count = await count_accountants(session)
    is_bootstrap = user_count == 0
    if is_bootstrap:
        if role != Role.superuser:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The first registered user must be a superuser",
            )
        firm = await get_or_create_firm(
            session, firm_id=firm_id, firm_name=firm_name or "Default Firm"
        )
    else:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication is required to register additional users",
            )
        else:
            current_role = Role(current_user.role.value)
            if current_role == Role.firm_admin:
                if role == Role.superuser:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Firm admins cannot create superusers",
                    )
                firm = await get_or_create_firm(session, firm_id=current_user.firm_id)
            elif current_role == Role.superuser:
                firm = await get_or_create_firm(
                    session, firm_id=firm_id, firm_name=firm_name
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only firm admins and superusers can register users",
                )

    user = Accountant(
        firm_id=firm.id,
        email=email,
        password_hash=await hash_password_async(password),
        role=RoleEnum(role.value),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_or_create_firm(
    session: AsyncSession, *, firm_id: int | None = None, firm_name: str | None = None
) -> Firm:
    """Resolve an existing firm or create one by name."""
    if firm_id is not None:
        firm = await session.get(Firm, firm_id)
        if not firm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Firm with id {firm_id} not found",
            )
        return firm
    if not firm_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="firm_id or firm_name is required",
        )

    firm = (
        await session.execute(select(Firm).where(Firm.name == firm_name))
    ).scalar_one_or_none()
    if firm:
        return firm
    firm = Firm(name=firm_name)
    session.add(firm)
    await session.flush()
    return firm


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token from payload data."""
    payload = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    payload.update({"exp": expire})
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
